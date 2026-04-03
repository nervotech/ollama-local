from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from ollama import chat, ChatResponse
from tools.tool_registery import TOOLS_REGISTRY as modeltools
from models import MODELS

app = Flask(__name__)
CORS(app)
print("Registered tools:", list(modeltools.values()))

@app.route('/')
def index():
    return {"code": 200, "message": "OK", "data":""}

@app.route('/models', methods=['GET'])
def get_models():
    from models import MODELS
    return jsonify({"code": 200, "message": "OK", "data": MODELS})

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
        {"role": "system", "content": "You are a helpful assistant. Keep your answers short and helpful. Only use a tool when it is truly required to answer the user.Markdown response format is preferred."}
    ] + user_messages

    responseMessage = []
    response = chat(
        model=model.get('model'),
        messages=messages,
        think=model.get('think'),
        tools=modeltools.values() if model.get('tools') else None
    )

    # Handle tool calls
    tool_outputs = []
    if response.message.tool_calls:
        tools = []
        for call in response.message.tool_calls:
            tool_name = call["function"]["name"]
            try:
                tool_desc = modeltools.get(tool_name).get("desc") if modeltools.get(tool_name) else "No description"
                args = call["function"]["arguments"]
                result = modeltools.get(tool_name).get("call")(**args)
                tool_outputs.append({"role": "tool", "content": f"Tool name:{tool_name}\nOutput: {result}.\n Only use this if the user query requires this information. If not, ignore this output."})
                tools.append(tool_name)
            except Exception as e:
                tool_outputs.append({"role": "tool", "content": f"Tool name:{tool_name}\nOutput:''\n Only use this if the user query requires this information. If not, ignore this output."})
                print(f"Error calling tool {tool_name}: {e}")
        if tool_outputs:
            followup = chat(
                model=model.get('model'),
                messages=messages + tool_outputs,
                think=model.get('think'),
                tools=modeltools.values() if model.get('tools') else None
            )
            responseMessage.append({**followup.message.model_dump(), "tools_used": tools})
    else:
        responseMessage.append({**response.message.model_dump(), "tools_used": []})

    return jsonify({"code": 200, "message": "OK", "data": responseMessage})