from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from ollama import chat, ChatResponse
from tools.tool_registery import TOOLS_REGISTRY as modeltools
from models import MODELS
from tools.webtools import get_latest_news, access_web_url

MAX_TOOL_ITERATIONS = 20  # prevent infinite loops

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return {"code": 200, "message": "OK", "data":""}

@app.route('/models', methods=['GET'])
def get_models():
    from models import MODELS
    return jsonify({"code": 200, "message": "OK", "data": MODELS})

def tool_response(tool_name, args):
    try:
        
        result = modeltools.get(tool_name).get("call")(**args)
        return {"role": "tool", "content": f"Tool name:{tool_name}\nOutput: {result}.\n Only use this if the user query requires this information. If not, ignore this output."}
        tools.append(tool_name)
    except Exception as e:
        return {"role": "tool", "content": f"Tool name:{tool_name}\nOutput:''\n Only use this if the user query requires this information. If not, ignore this output."}
        print(f"Error calling tool {tool_name}: {e}")


def execute_with_tools(model, messages, think, tools_enabled):
    tools_used = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = chat(
            model=model,
            messages=messages,
            think=think,
            tools=modeltools.values() if tools_enabled else None
        )

        msg = response.message

        # If no tool calls → final answer
        if not msg.tool_calls:
            return msg.model_dump(), tools_used

        # Handle tool calls
        tool_outputs = []
        for call in msg.tool_calls:
            tool_name = call["function"]["name"]
            args = call["function"]["arguments"]

            tool_outputs.append(tool_response(tool_name, args))
            tools_used.append(tool_name)

        # Append assistant tool call + tool outputs
        messages.append(msg.model_dump())
        messages.extend(tool_outputs)

    # Safety fallback
    return {
        "role": "assistant",
        "content": "Max tool iterations reached. Unable to complete request."
    }, tools_used

@app.route('/chat', methods=['POST'])
def ollama_chat():
    data = request.get_json()

    model_key = data.get("model")
    if model_key not in MODELS:
        return jsonify({"code": 400, "message": "Invalid model"}), 400

    model = MODELS[model_key]

    user_messages = data.get("message", [])
    if not isinstance(user_messages, list):
        return jsonify({"code": 400, "message": "Messages must be a list"}), 400

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Keep answers short. Use tools only when truly required. Keep your thinking short and precise. If you are not sure about some think tell that you don't know. Avoid halucination. "
        }
    ] + user_messages

    final_response, tools_used = execute_with_tools(
        model=model.get('model'),
        messages=messages,
        think=model.get('think'),
        tools_enabled=model.get('tools')
    )

    return jsonify({
        "code": 200,
        "message": "OK",
        "data": [{**final_response, "tools_used": tools_used}]
    })