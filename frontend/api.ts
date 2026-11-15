import axios from "axios";

// Create Axios instance
const api = axios.create({
  baseURL: "http://127.0.0.1:5000", // your base URL
  timeout: 0, // optional timeout
  headers: {
    "Content-Type": "application/json",
  },
});

export function sendMessage(message, model) {
    return api.post("/chat_stream", { "message": message, "model": model });
}

export function getModels() {
    return api.get("/models");
}

export default api;
