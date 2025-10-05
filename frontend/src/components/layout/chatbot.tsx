import { useState, useEffect } from "react";
import { Card, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { agentModes } from "@/data/agent-modes";
import { motion, AnimatePresence } from "framer-motion";
import PaperGraph from "@/components/custom/PaperGraph";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE_URL = "http://localhost:8082";
const USER_ID = "u_999";

export function Chatbot() {
    const [activeMode, setActiveMode] = useState("inquiry-agent");
    const [messages, setMessages] = useState<{ text: string; sender: "user" | "bot" }[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);

    useEffect(() => {
        const timer = setTimeout(() => setOpen(true), 500);
        return () => clearTimeout(timer);
    }, []);

    // Reset messages khi chuyển đổi mode
    useEffect(() => {
        setMessages([]);
    }, [activeMode]);

    const createSession = async (): Promise<{ userId: string; sessionId: string; appName: string }> => {
        const generatedSessionId = uuidv4();
        const response = await fetch(`${API_BASE_URL}/apps/adk-agent/users/${USER_ID}/sessions/${generatedSessionId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        return {
            userId: data.userId,
            sessionId: data.id,
            appName: data.appName
        };
    };

    const handleCreateNewSession = async () => {
        try {
            setLoading(true);
            const sessionData = await createSession();
            setSessionId(sessionData.sessionId);
            setMessages([]);
            setMessages([{ text: `New session created! Session ID: ${sessionData.sessionId}`, sender: "bot" }]);
        } catch (error) {
            console.error("Failed to create session:", error);
            setMessages([{ text: `Error creating session: ${error instanceof Error ? error.message : "Unknown error"}`, sender: "bot" }]);
        } finally {
            setLoading(false);
        }
    };

    const callApi = async (prompt: string) => {
        if (!sessionId) {
            return "Please create a session first by clicking the 'New Session' button.";
        }
        
        setLoading(true);
        let fullResponse = "";
        let streamingMessageAdded = false;
        
        try {
            const response = await fetch(`${API_BASE_URL}/run_sse`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    app_name: "adk-agent",
                    user_id: USER_ID,
                    session_id: sessionId,
                    new_message: {
                        role: "user",
                        parts: [{
                            text: prompt
                        }]
                    },
                    streaming: true
                })
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            // Handle SSE streaming response
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error("Response body is not readable");
            }

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonData = JSON.parse(line.substring(6));
                            
                            // Extract text from the response
                            if (jsonData.content?.parts) {
                                for (const part of jsonData.content.parts) {
                                    if (part.text) {
                                        fullResponse += part.text;
                                        
                                        // Update the bot message in real-time
                                        setMessages(prev => {
                                            const newMessages = [...prev];
                                            const lastMessage = newMessages[newMessages.length - 1];
                                            
                                            // If last message is from bot and is our streaming message, update it
                                            if (lastMessage?.sender === "bot" && streamingMessageAdded) {
                                                newMessages[newMessages.length - 1] = {
                                                    text: fullResponse,
                                                    sender: "bot"
                                                };
                                            } else {
                                                // Add new bot message
                                                newMessages.push({
                                                    text: fullResponse,
                                                    sender: "bot"
                                                });
                                                streamingMessageAdded = true;
                                            }
                                            return newMessages;
                                        });
                                    }
                                }
                            }
                        } catch (e) {
                            console.error("Failed to parse SSE data:", e);
                        }
                    }
                }
            }

            return fullResponse || "No response received from agent.";
        } catch (error) {
            console.error("API call failed:", error);
            return `Error: Unable to connect to the agent. ${error instanceof Error ? error.message : "Unknown error"}`;
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async () => {
        if (!inputValue.trim()) return;
        const userMessage = inputValue;
        setMessages([...messages, { text: userMessage, sender: "user" }]);
        setInputValue("");

        const botResponse = await callApi(userMessage);
        
        // Only add bot message if streaming didn't already add it
        setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage?.sender === "bot" && lastMessage?.text === botResponse) {
                return prev; // Message already added by streaming
            }
            return [...prev, { text: botResponse, sender: "bot" }];
        });
    };

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    initial={{ x: "100%", opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: "100%", opacity: 0 }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                    className="fixed top-0 right-0 h-full z-50 flex"
                >
                    <Card className="w-[600px] h-full flex flex-col bg-black border-l border-slate-600/50 rounded-none overflow-hidden py-2 shadow-2xl">
                        <CardHeader className="flex justify-between items-center py-2 px-4 border-b border-slate-600/50">
                            <div className="flex items-center gap-2">
                                <h2 className="text-sm font-semibold text-white">Choose the Agent Mode</h2>
                                <Button 
                                    variant="outline" 
                                    size="sm" 
                                    onClick={handleCreateNewSession}
                                    disabled={loading}
                                    className="text-xs"
                                >
                                    New Session
                                </Button>
                            </div>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="secondary" size="sm">
                                        {agentModes.find((m) => m.value === activeMode)?.label}
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent className="w-50">
                                    <DropdownMenuLabel>Choose Mode</DropdownMenuLabel>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuRadioGroup value={activeMode} onValueChange={setActiveMode}>
                                        {agentModes.map((mode) => (
                                            <DropdownMenuRadioItem key={mode.value} value={mode.value}>
                                                {mode.label}
                                            </DropdownMenuRadioItem>
                                        ))}
                                    </DropdownMenuRadioGroup>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </CardHeader>

                        <div className="flex-1 px-4 py-3 overflow-y-auto text-white flex flex-col gap-3 scrollbar-thin scrollbar-thumb-gray-500 scrollbar-track-gray-900">
                            {messages.length === 0 && (
                                <div className="text-gray-400 italic text-sm space-y-2 p-4">
                                    <p className="text-lg font-semibold">Welcome to the GoK Super Agent! 🚀</p>
                                    <p>Start by creating a new session, then ask me anything about scientific research.</p>
                                </div>
                            )}
                            {messages.map((msg, index) => (
                                <div
                                    key={index}
                                    className={`p-3 rounded-lg max-w-[85%] shadow-lg ${msg.sender === "user"
                                        ? "self-end bg-blue-600 text-white"
                                        : "self-start bg-gray-800 text-white border border-gray-700"
                                        }`}
                                >
                                    {msg.sender === "bot" ? (
                                        <div className="prose-chatbot">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.text}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <p className="text-base leading-relaxed">{msg.text}</p>
                                    )}
                                </div>
                            ))}
                            {loading && (
                                <div className="self-start text-gray-400 italic text-sm flex items-center gap-2 p-3">
                                    <div className="animate-pulse">●</div>
                                    <span>Bot is thinking...</span>
                                </div>
                            )}
                            {
                                activeMode === "pro-agent" && (<PaperGraph />)
                            }
                        </div>

                        <CardFooter className="border-t border-slate-600/50 p-4 flex gap-2">
                            <Input
                                type="text"
                                placeholder="Ask me anything about scientific research..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                className="flex-1 rounded-lg border border-gray-600 px-4 py-3 text-base bg-black text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                                disabled={loading}
                            />
                            <Button 
                                variant="secondary" 
                                size="default" 
                                onClick={handleSend} 
                                disabled={loading || !inputValue.trim()}
                                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors"
                            >
                                Send
                            </Button>
                        </CardFooter>
                    </Card>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
