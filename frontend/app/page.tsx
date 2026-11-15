
'use client';

import { useState, useEffect, useRef } from "react";

import { getModels } from "@/api";
import { Message, ToolEvent } from "@/types";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Textarea } from "@/components/ui/textarea"

import {
  SquarePen,
  BrainCircuit,
  Wrench,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Terminal,
  Brain,
} from "lucide-react";

import { Button } from "@/components/ui/button";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Input } from "@/components/ui/input";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenuButton,
  SidebarMenu,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";


// =========================================
// EVENT TYPES
// =========================================

interface StreamEvent {
  event: string;
  id?: string;
  tool?: string;
  token?: string;
  thinking?: string;
  input?: any;
  result?: any;
  error?: string;
  message?: string;
  tools_used?: string[];
  model?: string;
  thinking_enabled?: boolean;
}


// =========================================
// MAIN COMPONENT
// =========================================

export default function Home() {

  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState<Message[]>([]);

  const [models, setModels] = useState<any>([]);

  const [selectedModel, setSelectedModel] =
    useState("youtu/youtu");

  // Thinking mode is OFF by default for faster responses.
  const [thinkEnabled, setThinkEnabled] = useState(true);

  const [loading, setLoading] = useState(false);

  const chatContainerRef = useRef<HTMLDivElement>(null);


  // =======================================
  // FETCH MODELS
  // =======================================

  useEffect(() => {

    async function fetchData() {

      try {

        const res = await getModels();

        const availableModels = res.data.data || [];
        setModels(availableModels);

        const firstModel = availableModels[0];
        if (firstModel) {
          setSelectedModel(firstModel);
        }

      } catch (error) {

        console.error("Model fetching failed:", error);

      }

    }

    fetchData();

  }, []);


  // =======================================
  // AUTO SCROLL
  // =======================================

  // =======================================
// SMART AUTO SCROLL
// =======================================

const shouldAutoScrollRef = useRef(true);

useEffect(() => {
  const container = chatContainerRef.current;

  if (!container) return;

  const handleScroll = () => {
    const distanceFromBottom =
      container.scrollHeight -
      container.scrollTop -
      container.clientHeight;

    shouldAutoScrollRef.current = distanceFromBottom < 100;
  };

  container.addEventListener("scroll", handleScroll);

  return () => {
    container.removeEventListener("scroll", handleScroll);
  };
}, []);

useEffect(() => {
  const container = chatContainerRef.current;

  if (!container || !shouldAutoScrollRef.current) return;

  container.scrollTop = container.scrollHeight;
}, [messages]);


  // =======================================
  // UPDATE MESSAGE
  // =======================================

  function updateAssistantMessage(

    index: number,

    updater: (message: Message) => Message

  ) {

    setMessages((prev) => {

      const copy = [...prev];

      if (!copy[index]) return prev;

      copy[index] = updater(copy[index]);

      return copy;

    });

  }


  // =======================================
  // APPEND THINKING
  // =======================================

  function appendThinking(

    index: number,

    thinking: string,

    thinkingText: { current: string }

  ) {

    thinkingText.current += thinking;

    updateAssistantMessage(index, (msg) => ({

      ...msg,

      thinking: thinkingText.current,

    }));

  }


  // =======================================
  // APPEND ANSWER TOKEN
  // =======================================

  function appendToken(

    index: number,

    token: string,

    assistantText: { current: string }

  ) {

    // Preserve the exact model output.
    // Never add spaces between streamed tokens.

    assistantText.current += token;

    updateAssistantMessage(index, (msg) => ({

      ...msg,

      content: assistantText.current,

    }));

  }


  // =======================================
  // UPDATE TOOL
  // =======================================

  function updateTool(

    index: number,

    toolId: string,

    updates: Partial<ToolEvent>

  ) {

    updateAssistantMessage(index, (msg) => {

      const tools = [...(msg.tool_events || [])];

      const toolIndex = tools.findIndex(

        (tool) => tool.id === toolId

      );


      if (toolIndex !== -1) {

        tools[toolIndex] = {

          ...tools[toolIndex],

          ...updates,

        };

      } else {

        tools.push({

          id: toolId,

          name: updates.name || "Unknown tool",

          status: updates.status || "running",

          ...updates,

        });

      }


      return {

        ...msg,

        tool_events: tools,

        tools_used: [

          ...new Set(

            tools.map((tool) => tool.name)

          ),

        ],

      };

    });

  }


  // =======================================
  // HANDLE SSE EVENTS
  // =======================================

  function handleEvent(

    event: StreamEvent,

    assistantIndex: number,

    assistantText: { current: string },

    thinkingText: { current: string }

  ) {

    switch (event.event) {


      // -----------------------------------
      // START
      // -----------------------------------

      case "start":

        console.log("Stream started:", event.model);

        break;


      // -----------------------------------
      // THINKING
      // -----------------------------------

      case "thinking":

        if (typeof event.thinking === "string") {

          appendThinking(

            assistantIndex,

            event.thinking,

            thinkingText

          );

        }

        break;


      // -----------------------------------
      // NORMAL TOKEN
      // -----------------------------------

      case "token":

        if (typeof event.token === "string") {

          appendToken(

            assistantIndex,

            event.token,

            assistantText

          );

        }

        break;


      // -----------------------------------
      // TOOL CALL
      // -----------------------------------

      case "tool_call": {

        const toolId = event.id || crypto.randomUUID();

        updateTool(assistantIndex, toolId, {

          name: event.tool || "Unknown tool",

          status: "running",

          input: event.input,

        });

        break;

      }


      // -----------------------------------
      // TOOL RUNNING
      // -----------------------------------

      case "tool_running": {

        if (!event.id) break;

        updateTool(assistantIndex, event.id, {

          name: event.tool || "Unknown tool",

          status: "running",

          input: event.input,

        });

        break;

      }


      // -----------------------------------
      // TOOL RESULT
      // -----------------------------------

      case "tool_result": {

        if (!event.id) break;

        updateTool(assistantIndex, event.id, {

          name: event.tool || "Unknown tool",

          status: "completed",

          result: event.result,

        });

        break;

      }


      // -----------------------------------
      // TOOL ERROR
      // -----------------------------------

      case "tool_error": {

        if (!event.id) break;

        updateTool(assistantIndex, event.id, {

          name: event.tool || "Unknown tool",

          status: "error",

          error: event.error || "Tool execution failed",

        });

        break;

      }


      // -----------------------------------
      // GENERAL ERROR
      // -----------------------------------

      case "error": {

        const errorMessage =
          event.message || "Unknown error";

        assistantText.current +=
          `\n\n**Error:** ${errorMessage}`;

        updateAssistantMessage(

          assistantIndex,

          (msg) => ({

            ...msg,

            content: assistantText.current,

          })

        );

        break;

      }


      // -----------------------------------
      // DONE
      // -----------------------------------

      case "done":

        console.log("Generation completed");

        break;


      default:

        console.log("Unknown event:", event);

    }

  }


  // =======================================
  // SEND MESSAGE
  // =======================================

  async function sendMessageAPI() {

    if (!message.trim() || loading) return;


    const userMessage: Message = {

      role: "user",

      content: message.trim(),
      

    };


    const assistantMessage: Message = {

      role: "assistant",

      content: "",

      thinking: "",

      tools_used: [],

      tool_events: [],

    };


    const updatedMessages = [

      ...messages,

      userMessage,

      assistantMessage,

    ];


    const assistantIndex = updatedMessages.length - 1;


    setMessages(updatedMessages);

    setMessage("");

    setLoading(true);


    const assistantText = { current: "" };

    const thinkingText = { current: "" };


    try {

      const res = await fetch(

        "http://localhost:5000/chat_stream",

        {

          method: "POST",

          headers: {

            "Content-Type": "application/json",

            "Accept": "text/event-stream",

          },

          body: JSON.stringify({

            model: selectedModel,

            message: [

              ...messages,

              userMessage,

            ],
            "think": thinkEnabled
          }),

        }

      );


      if (!res.ok) {

        throw new Error(

          `HTTP Error: ${res.status}`

        );

      }


      if (!res.body) {

        throw new Error("Response stream not available");

      }


      const reader = res.body.getReader();

      const decoder = new TextDecoder("utf-8");

      let buffer = "";


      // ===================================
      // PROCESS SSE BLOCK
      // ===================================

      function processBlock(block: string) {

        const lines = block.split(/\r?\n/);

        const dataLines = lines

          .filter((line) => line.startsWith("data:"))

          .map((line) => line.slice(5).replace(/^ /, ""));


        if (!dataLines.length) return;


        const data = dataLines.join("\n");


        if (!data || data === "[DONE]") return;


        try {

          const event: StreamEvent = JSON.parse(data);

          handleEvent(

            event,

            assistantIndex,

            assistantText,

            thinkingText

          );

        } catch (error) {

          console.error("Invalid SSE event:", data, error);

        }

      }


      // ===================================
      // READ STREAM
      // ===================================

      while (true) {

        const { value, done } = await reader.read();

        if (done) break;


        buffer += decoder.decode(value, {

          stream: true,

        });


        const blocks = buffer.split(/\r?\n\r?\n/);

        buffer = blocks.pop() || "";


        for (const block of blocks) {

          processBlock(block);

        }

      }


      // ===================================
      // FLUSH REMAINING DATA
      // ===================================

      buffer += decoder.decode();

      if (buffer.trim()) {

        processBlock(buffer);

      }


    } catch (error) {

      console.error("Chat error:", error);

      const errorMessage = error instanceof Error

        ? error.message

        : "Something went wrong";


      assistantText.current +=

        `\n\n**Error:** ${errorMessage}`;


      updateAssistantMessage(

        assistantIndex,

        (msg) => ({

          ...msg,

          content: assistantText.current,

        })

      );

    } finally {

      setLoading(false);

    }

  }


  // =======================================
  // RESET CHAT
  // =======================================

  function resetChat() {

    if (loading) return;

    setMessages([]);

    setMessage("");

  }


  // =======================================
  // MAIN UI
  // =======================================

  return (

    <SidebarProvider>

      <Sidebar>

        <SidebarHeader>

          <SidebarMenu>

            <SidebarMenuItem className="flex items-center gap-4 p-2">

              <BrainCircuit className="w-6 h-6" />

              <h2 className="text-xl font-bold">

                Jarvis

              </h2>

            </SidebarMenuItem>

          </SidebarMenu>

        </SidebarHeader>


        <SidebarContent className="p-2">

          <SidebarMenu>

            <SidebarMenuItem>

              <SidebarMenuButton

                onClick={resetChat}

                disabled={loading}

              >

                <SquarePen className="w-4 h-4" />

                New Chat

              </SidebarMenuButton>

            </SidebarMenuItem>

          </SidebarMenu>

        </SidebarContent>


        <SidebarFooter />

      </Sidebar>


      <main className="flex w-full min-w-0 text-gray-800 p-2">

        <SidebarTrigger />


        <div className="flex flex-col gap-2 w-full min-w-0">


          {/* CHAT AREA */}

          <div

            ref={chatContainerRef}

            className="flex-1 overflow-y-auto p-3 flex flex-col gap-5"

            style={{

              maxHeight: "calc(100vh - 100px)",

            }}

          >


            {messages.map((msg, index) => (

              <div

                key={index}

                className="flex flex-col gap-3 w-full"

              >


                {/* USER MESSAGE */}

                {msg.role === "user" && (

                  <div className="flex justify-end">

                    <div className="bg-zinc-100 rounded-2xl p-3 max-w-[80%] text-sm whitespace-pre-wrap">

                      {msg.content}

                    </div>

                  </div>

                )}


                {/* ASSISTANT MESSAGE */}

                {msg.role === "assistant" && (

                  <div className="flex flex-col gap-3 w-full">


                    {/* THINKING PANEL */}

                    {(msg.thinking || (thinkEnabled && loading && index === messages.length - 1)) && (

                      <ThinkingPanel

                        thinking={msg.thinking || ""}

                        isThinking={loading && index === messages.length - 1}

                      />

                    )}


                    {/* TOOL EVENTS */}

                    {msg.tool_events &&

                      msg.tool_events.length > 0 && (

                        <div className="flex flex-col gap-3">

                          <div className="flex items-center gap-2 text-xs font-semibold text-gray-500">

                            <Wrench className="w-4 h-4" />

                            Tools used

                            <span className="bg-gray-100 px-2 py-1 rounded-full">

                              {msg.tool_events.length}

                            </span>

                          </div>


                          {msg.tool_events.map((tool) => (

                            <ToolCard

                              key={tool.id}

                              tool={tool}

                            />

                          ))}

                        </div>

                      )}


                    {/* FINAL ANSWER */}

                    {msg.content && (

                      <div className="bg-slate-100 rounded-2xl p-4 text-sm overflow-x-auto">

                        <div className="prose prose-sm max-w-none break-words

                          prose-headings:font-semibold

                          prose-pre:bg-zinc-900

                          prose-pre:text-white

                          prose-pre:rounded-xl

                          prose-code:text-indigo-600

                          prose-a:text-blue-600

                          prose-a:underline

                          prose-table:border-collapse

                          prose-th:border

                          prose-th:p-2

                          prose-td:border

                          prose-td:p-2

                        ">

                          <ReactMarkdown

                            remarkPlugins={[remarkGfm]}

                          >

                            {msg.content}

                          </ReactMarkdown>

                        </div>

                      </div>

                    )}


                  </div>

                )}

              </div>

            ))}


            {/* THINKING INDICATOR */}

            {loading && messages.length === 0 && (

              <div className="flex items-center gap-2 text-sm text-gray-500">

                <Loader2 className="w-4 h-4 animate-spin" />

                Jarvis is thinking...

              </div>

            )}


          </div>


          {/* INPUT AREA */}

          <div className="flex items-center gap-2 sticky bottom-0 bg-white p-2 border-t">


            <Textarea

              value={message}

              onChange={(e) => setMessage(e.target.value)}

              onKeyDown={(e) => {

                if (

                  e.key === "Enter" &&

                  !e.shiftKey

                ) {

                  e.preventDefault();

                  sendMessageAPI();

                }

              }}

              placeholder="Type your message..."

              disabled={loading}

            />


            <Select

              value={selectedModel}

              onValueChange={setSelectedModel}

              disabled={loading}

            >

              <SelectTrigger className="w-[180px]">

                <SelectValue placeholder="Model" />

              </SelectTrigger>


              <SelectContent>

                <SelectGroup>

                  {models.map(

                    (model: any) => (

                      <SelectItem

                        key={model}

                        value={model}

                      >

                        {model}

                      </SelectItem>

                    )

                  )}

                </SelectGroup>

              </SelectContent>

            </Select>


            <Button
              type="button"
              variant={thinkEnabled ? "default" : "outline"}
              size="sm"
              disabled={loading}
              aria-pressed={thinkEnabled}
              onClick={() => setThinkEnabled((enabled) => !enabled)}
              className="shrink-0 gap-2"
              title={
                thinkEnabled
                  ? "Thinking mode enabled"
                  : "Thinking mode disabled"
              }
            >
              <Brain className="w-4 h-4" />
              Think {thinkEnabled ? "On" : "Off"}
            </Button>

            <Button

              onClick={sendMessageAPI}

              disabled={loading || !message.trim()}

            >

              Send

            </Button>


          </div>

        </div>

      </main>

    </SidebarProvider>

  );

}


// =========================================
// THINKING PANEL
// =========================================

function ThinkingPanel({

  thinking,

  isThinking,

}: {

  thinking: string;

  isThinking: boolean;

}) {

  const [expanded, setExpanded] = useState(true);


  return (

    <div className="border border-purple-200 rounded-xl bg-purple-50 overflow-hidden">


      {/* HEADER */}

      <button

        onClick={() => setExpanded(!expanded)}

        className="w-full flex items-center justify-between p-3 text-left hover:bg-purple-100 transition-colors"

      >

        <div className="flex items-center gap-2">


          <Brain className="w-4 h-4 text-purple-600" />


          <span className="font-medium text-purple-800 text-sm">

            {isThinking ? "Thinking..." : "Thought process"}

          </span>


          {isThinking && (

            <Loader2 className="w-3 h-3 animate-spin text-purple-600" />

          )}

        </div>


        {expanded ? (

          <ChevronDown className="w-4 h-4 text-purple-600" />

        ) : (

          <ChevronRight className="w-4 h-4 text-purple-600" />

        )}

      </button>


      {/* THINKING CONTENT */}

      {expanded && (

        <div className="border-t border-purple-200 p-3">


          {thinking ? (

            <div className="text-sm text-purple-950 leading-7 prose prose-sm max-w-none break-words">

              <ReactMarkdown

                remarkPlugins={[remarkGfm]}

              >

                {thinking}

              </ReactMarkdown>

              {isThinking && (

                <span className="inline-block w-2 h-4 ml-1 bg-purple-500 animate-pulse align-middle" />

              )}

            </div>

          ) : (

            <div className="text-xs text-purple-500">

              Waiting for thinking output...

            </div>

          )}


        </div>

      )}


    </div>

  );

}


// =========================================
// TOOL CARD
// =========================================

function ToolCard({ tool }: { tool: ToolEvent }) {

  const [expanded, setExpanded] = useState(false);


  function formatData(data: any) {

    if (typeof data === "string") {

      try {

        return JSON.stringify(

          JSON.parse(data),

          null,

          2

        );

      } catch {

        return data;

      }

    }

    return JSON.stringify(data, null, 2);

  }


  return (

    <div className="border rounded-xl bg-white overflow-hidden text-sm">


      {/* HEADER */}

      <button

        onClick={() => setExpanded(!expanded)}

        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 text-left"

      >

        <div className="flex items-center gap-2 min-w-0">


          {tool.status === "running" && (

            <Loader2 className="w-4 h-4 animate-spin text-blue-500 shrink-0" />

          )}


          {tool.status === "completed" && (

            <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />

          )}


          {tool.status === "error" && (

            <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />

          )}


          <span className="font-medium truncate">

            {tool.name}

          </span>


          <span className="text-xs text-gray-500">

            {tool.status === "running" && "Running"}

            {tool.status === "completed" && "Completed"}

            {tool.status === "error" && "Failed"}

          </span>


        </div>


        {expanded ? (

          <ChevronDown className="w-4 h-4 shrink-0" />

        ) : (

          <ChevronRight className="w-4 h-4 shrink-0" />

        )}

      </button>


      {/* DETAILS */}

      {expanded && (

        <div className="border-t p-3 flex flex-col gap-3 bg-gray-50">


          {tool.input !== undefined && (

            <div>

              <div className="flex items-center gap-2 font-semibold text-xs mb-2">

                <Terminal className="w-3 h-3" />

                Tool Input

              </div>


              <pre className="bg-zinc-900 text-green-300 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap">

                {formatData(tool.input)}

              </pre>

            </div>

          )}


          {tool.result !== undefined && (

            <div>

              <div className="font-semibold text-xs mb-2">

                Tool Result

              </div>


              <pre className="bg-zinc-900 text-white rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap">

                {formatData(tool.result)}

              </pre>

            </div>

          )}


          {tool.error && (

            <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg p-3 text-xs">

              <div className="flex items-center gap-2 font-semibold mb-1">

                <AlertCircle className="w-4 h-4" />

                Tool Error

              </div>

              {tool.error}

            </div>

          )}


        </div>

      )}

    </div>

  );

}