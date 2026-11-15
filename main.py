
import json
import uuid
import logging

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

import ollama
from ollama import chat

from tools.tool_registery import TOOLS_REGISTRY as modeltools
from models import MODELS

# =========================================
# CONFIGURATION
# =========================================

MAX_TOOL_ITERATIONS = 20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def load_prompt():
    with open('prompts/system.md','r') as f:
        return f.read()

SYSTEM_PROMPT = load_prompt()

def get_think_setting(data, model_cfg):

    requested_think = data.get("think")

    if isinstance(requested_think, bool):
        return requested_think

    return bool(model_cfg.get("think", False))


# =========================================
# SSE HELPERS
# =========================================

def send_event(event_name, data=None):

    payload = {"event": event_name}

    if data:
        payload.update(data)

    return (
        f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
    )


def serialize_result(result):

    return json.dumps(
        result,
        ensure_ascii=False,
        default=str
    )


# =========================================
# INPUT VALIDATION
# =========================================

def validate_request(data):

    if not isinstance(data, dict):
        return None, "Invalid JSON request"

    model_key = data.get("model")

    if not isinstance(model_key, str) or model_key not in MODELS:
        return None, "Invalid model"

    messages = data.get("message", [])

    if not isinstance(messages, list) or not messages:
        return None, "Messages must be a non-empty list"

    for message in messages:

        if not isinstance(message, dict):
            return None, "Each message must be an object"

        if message.get("role") not in ("user", "assistant", "tool"):
            return None, "Invalid message role"

        if not isinstance(message.get("content", ""), str):
            return None, "Message content must be a string"

    model_cfg = MODELS[model_key]

    return {
        "model_key": model_key,
        "model": model_cfg["model"],
        "think": get_think_setting(data, model_cfg),
        "tools_enabled": bool(model_cfg.get("tools", False)),
        "messages": messages
    }, None


# =========================================
# TOOL HELPERS
# =========================================

def get_tool_call_data(call):

    if hasattr(call, "model_dump"):
        call = call.model_dump()

    if not isinstance(call, dict):
        return {"name": None, "arguments": {}}

    function = call.get("function", {})

    if hasattr(function, "model_dump"):
        function = function.model_dump()

    if not isinstance(function, dict):
        function = {}

    arguments = function.get("arguments", {})

    if isinstance(arguments, str):

        try:
            arguments = json.loads(arguments)

        except json.JSONDecodeError:
            arguments = {}

    if not isinstance(arguments, dict):
        arguments = {}

    return {
        "name": function.get("name"),
        "arguments": arguments
    }


def execute_tool(tool_name, arguments):

    if tool_name not in modeltools:
        raise ValueError(f"Tool '{tool_name}' is not registered")

    callback = modeltools[tool_name].get("call")

    if not callable(callback):
        raise ValueError(f"Tool '{tool_name}' is not callable")

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object")

    return callback(**arguments)


def get_tool_definitions(tools_enabled):

    if not tools_enabled:
        return None

    return list(modeltools.values())


def create_tool_message(tool_name, result):

    return {
        "role": "tool",
        "content": serialize_result(result)
    }


# =========================================
# TOOL CALL ACCUMULATION
# =========================================

def merge_tool_calls(collected, incoming):

    """
    Merge streamed tool calls by their position.

    This prevents repeated chunks from creating duplicate
    tool executions and allows dictionary arguments to
    accumulate across chunks.
    """

    for index, call in enumerate(incoming):

        tool_data = get_tool_call_data(call)

        if not tool_data["name"]:
            continue

        if index >= len(collected):

            collected.append({
                "name": tool_data["name"],
                "arguments": tool_data["arguments"]
            })

            continue

        existing = collected[index]

        existing["name"] = tool_data["name"]

        existing["arguments"].update(
            tool_data["arguments"]
        )

    return collected


# =========================================
# BASIC ROUTES
# =========================================

@app.route("/")
def index():

    return jsonify({
        "code": 200,
        "message": "OK",
        "data": ""
    })


@app.route("/models", methods=["GET"])
def get_models():

    try:

        models = ollama.list()

        return jsonify({
            "code": 200,
            "message": "OK",
            "data": [
                model.model
                for model in models.models
            ]
        })

    except Exception as error:

        logger.exception("Failed to retrieve models")

        return jsonify({
            "code": 500,
            "message": str(error)
        }), 500


# =========================================
# NON-STREAMING TOOL EXECUTION
# =========================================

def execute_with_tools(model, messages, think, tools_enabled):

    tools_used = []

    for iteration in range(MAX_TOOL_ITERATIONS):

        logger.info(
            "Model iteration: %s | Thinking: %s",
            iteration + 1,
            think
        )

        response = chat(
            model=model,
            messages=messages,
            think=think,
            tools=get_tool_definitions(tools_enabled)
        )

        assistant_message = response.message.model_dump(
            exclude_none=True
        )

        tool_calls = getattr(
            response.message,
            "tool_calls",
            None
        )

        messages.append(assistant_message)

        if not tool_calls:

            return assistant_message, tools_used

        for call in tool_calls:

            tool_data = get_tool_call_data(call)

            tool_name = tool_data["name"]
            arguments = tool_data["arguments"]

            if not tool_name:
                continue

            if tool_name not in tools_used:
                tools_used.append(tool_name)

            try:

                result = execute_tool(
                    tool_name,
                    arguments
                )

                messages.append(
                    create_tool_message(
                        tool_name,
                        result
                    )
                )

            except Exception as error:

                logger.exception(
                    "Tool execution failed: %s",
                    tool_name
                )

                messages.append({
                    "role": "tool",
                    "content": (
                        f"Tool: {tool_name}\n"
                        f"Error: {str(error)}"
                    )
                })

    return {
        "role": "assistant",
        "content": "Maximum tool iterations reached."
    }, tools_used


# =========================================
# NON-STREAMING CHAT
# =========================================

@app.route("/chat", methods=["POST"])
def chat_non_stream():

    data = request.get_json(silent=True)

    config, error = validate_request(data)

    if error:

        return jsonify({
            "code": 400,
            "message": error
        }), 400

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ] + config["messages"]

    try:

        final_message, tools_used = execute_with_tools(
            model=config["model"],
            messages=messages,
            think=config["think"],
            tools_enabled=config["tools_enabled"]
        )

        return jsonify({
            "code": 200,
            "message": "OK",
            "data": {
                "response": final_message,
                "tools_used": tools_used,
                "thinking_enabled": config["think"]
            }
        })

    except Exception as error:

        logger.exception("Chat request failed")

        return jsonify({
            "code": 500,
            "message": str(error)
        }), 500


# =========================================
# STREAMING CHAT
# =========================================

@app.route("/chat_stream", methods=["POST"])
def chat_stream():

    data = request.get_json(silent=True)

    config, error = validate_request(data)

    if error:

        return jsonify({
            "code": 400,
            "message": error
        }), 400

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ] + config["messages"]

    model = config["model"]
    think = config["think"]
    tools_enabled = config["tools_enabled"]

    def generate():

        tools_used = []

        try:

            yield send_event("start", {
                "model": model,
                "thinking_enabled": think
            })

            for iteration in range(MAX_TOOL_ITERATIONS):

                logger.info(
                    "Streaming iteration: %s | Thinking: %s",
                    iteration + 1,
                    think
                )

                stream = chat(
                    model=model,
                    messages=messages,
                    tools=get_tool_definitions(tools_enabled),
                    think=think,
                    stream=True
                )

                assistant_message = {
                    "role": "assistant",
                    "content": "",
                    "thinking": ""
                }

                collected_tool_calls = []

                # =================================
                # READ MODEL STREAM
                # =================================

                for chunk in stream:

                    msg = chunk.message

                    # Thinking
                    thinking = getattr(
                        msg,
                        "thinking",
                        None
                    )

                    if think and thinking:

                        assistant_message["thinking"] += thinking

                        yield send_event("thinking", {
                            "thinking": thinking
                        })

                    # Tool calls
                    chunk_tool_calls = getattr(
                        msg,
                        "tool_calls",
                        None
                    )

                    if chunk_tool_calls:

                        merge_tool_calls(
                            collected_tool_calls,
                            chunk_tool_calls
                        )

                    # Normal content
                    content = getattr(
                        msg,
                        "content",
                        None
                    )

                    if content:

                        assistant_message["content"] += content

                        yield send_event("token", {
                            "token": content
                        })

                # =================================
                # EXECUTE TOOL CALLS
                # =================================

                if collected_tool_calls:

                    assistant_message["tool_calls"] = [
                        {
                            "type": "function",
                            "function": {
                                "name": item["name"],
                                "arguments": item["arguments"]
                            }
                        }
                        for item in collected_tool_calls
                    ]

                    if not assistant_message["thinking"]:
                        assistant_message.pop("thinking")

                    messages.append(assistant_message)

                    for item in collected_tool_calls:

                        tool_id = str(uuid.uuid4())

                        tool_name = item["name"]
                        arguments = item["arguments"]

                        if tool_name not in tools_used:
                            tools_used.append(tool_name)

                        yield send_event("tool_call", {
                            "id": tool_id,
                            "tool": tool_name,
                            "input": arguments
                        })

                        yield send_event("tool_running", {
                            "id": tool_id,
                            "tool": tool_name,
                            "input": arguments
                        })

                        try:

                            result = execute_tool(
                                tool_name,
                                arguments
                            )

                            messages.append(
                                create_tool_message(
                                    tool_name,
                                    result
                                )
                            )

                            yield send_event("tool_result", {
                                "id": tool_id,
                                "tool": tool_name,
                                "result": result
                            })

                        except Exception as error:

                            logger.exception(
                                "Tool execution failed: %s",
                                tool_name
                            )

                            error_message = str(error)

                            messages.append({
                                "role": "tool",
                                "content": (
                                    f"Tool: {tool_name}\n"
                                    f"Error: {error_message}"
                                )
                            })

                            yield send_event("tool_error", {
                                "id": tool_id,
                                "tool": tool_name,
                                "error": error_message
                            })

                    # Continue model generation using tool results
                    continue

                # =================================
                # FINAL ANSWER
                # =================================

                if not assistant_message["thinking"]:
                    assistant_message.pop("thinking")

                messages.append(assistant_message)

                yield send_event("done", {
                    "tools_used": tools_used,
                    "message": assistant_message["content"]
                })

                return

            # Maximum iterations reached

            yield send_event("error", {
                "message": "Maximum tool iterations reached."
            })

            yield send_event("done", {
                "tools_used": tools_used
            })

        except GeneratorExit:
            logger.info("Client disconnected from stream")
            raise

        except Exception as error:

            logger.exception("Chat streaming failed")

            yield send_event("error", {
                "message": str(error)
            })

            yield send_event("done", {
                "tools_used": tools_used
            })

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# =========================================
# RUN SERVER
# =========================================

if __name__ == "__main__":

    print(ollama.list())

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True
    )
