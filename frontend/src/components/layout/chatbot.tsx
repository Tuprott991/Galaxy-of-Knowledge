import { useState, useEffect, useCallback } from "react";
import { Card, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { useGlobal } from "@/context/GlobalContext";

const API_BASE_URL = "http://localhost:8082";
const USER_ID = "u_999";

export function Chatbot() {
    const { selectedPaperId } = useGlobal();
    const [activeMode, setActiveMode] = useState("inquiry-agent");
    const [messages, setMessages] = useState<{ text: string; sender: "user" | "bot" }[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);

    const hypoContent = `**New Hypothesis
Title:
AI-Augmented Antibody Repertoire Mining for Next-Generation Vaccine and Therapeutic Discovery
Core Idea:
Combine naive murine antibody repertoire datasets (PMC5761896) with transformer-based protein language models (PMC8534217, PMC9982045) to generate novel antibody scaffolds exhibiting enhanced binding affinity and cross-pathogen coverage — thus accelerating biologics discovery and global pandemic preparedness.
**Reasoning Summary
PMC5761896 — Supplies raw, unbiased murine repertoire sequences, a diverse immunogenomic substrate rarely used in AI pipelines.
PMC8534217 — Shows that transfer learning improves antibody structure–function inference from existing repertoires.
PMC9982045 — Demonstrates generative AI in designing functional antibodies and vaccines.
→ Together, they form a pipeline for reviving legacy immunogenomic datasets and coupling them with modern foundation models.`;

    useEffect(() => {
        const timer = setTimeout(() => setOpen(true), 500);
        return () => clearTimeout(timer);
    }, []);

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

    const handleCreateNewSession = useCallback(async () => {
        try {
            setLoading(true);
            const sessionData = await createSession();
            setSessionId(sessionData.sessionId);

            if (selectedPaperId) {
                setMessages([{
                    text: `📄 **Paper ID:** \`${selectedPaperId}\`\n\nNew session created! You can now ask questions about this paper.`,
                    sender: "bot"
                }]);
            } else {
                setMessages([{ text: `New session created! Session ID: ${sessionData.sessionId}`, sender: "bot" }]);
            }
        } catch (error) {
            console.error("Failed to create session:", error);
            setMessages([{ text: `Error creating session: ${error instanceof Error ? error.message : "Unknown error"}`, sender: "bot" }]);
        } finally {
            setLoading(false);
        }
    }, [selectedPaperId]);

    useEffect(() => {
        if (selectedPaperId) {
            setMessages([{
                text: `📄 **Paper ID:** \`${selectedPaperId}\`\n\nCreating new session for this paper...`,
                sender: "bot"
            }]);
            handleCreateNewSession();
        } else {
            setMessages([]);
        }
    }, [selectedPaperId, handleCreateNewSession]);

    useEffect(() => {
        if (selectedPaperId) {
            setMessages([{
                text: activeMode === "hypo-agent" ? hypoContent : `📄 **Paper ID:** \`${selectedPaperId}\`\n\nI'm here to help you analyze this paper. Feel free to ask questions about its content, methodology, findings, or any other aspect!`,
                sender: "bot"
            }]);
        } else {
            setMessages([]);
        }
    }, [activeMode, selectedPaperId, hypoContent]);

    const handleSend = async () => {
        if (!inputValue.trim()) return;

        const isFirstUserMessage = messages.every(msg => msg.sender === "bot");

        if (isFirstUserMessage && activeMode === "hypo-agent") {
            setMessages([...messages, { text: inputValue, sender: "user" }]);
        } else {
            setMessages([...messages, { text: inputValue, sender: "user" }]);
        }
        setInputValue("");

        // Add thinking message
        setMessages(prev => [...prev, { text: "Thinking...", sender: "bot" }]);

        // Simulate response delay
        setTimeout(() => {
            const fixedResponse = hypoContent;
            setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage?.sender === "bot") {
                    newMessages[newMessages.length - 1] = { text: fixedResponse, sender: "bot" };
                }
                return newMessages;
            });
        }, 1000); // 1 second delay to simulate thinking
    };

    const getDisplayMessages = (msgs: { text: string; sender: "user" | "bot" }[]) => {
        let lastBotIndex = -1;
        for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].sender === "bot") {
                lastBotIndex = i;
                break;
            }
        }
        if (lastBotIndex === -1) {
            return msgs.slice(-1); // last message, probably user
        }
        let userIndex = -1;
        for (let i = lastBotIndex - 1; i >= 0; i--) {
            if (msgs[i].sender === "user") {
                userIndex = i;
                break;
            }
        }
        if (userIndex === -1) {
            return [msgs[lastBotIndex]];
        }
        return [msgs[userIndex], msgs[lastBotIndex]];
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
                                {/* <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCreateNewSession}
                                    disabled={loading}
                                    className="text-xs"
                                >
                                    New Session
                                </Button> */}
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
                            {getDisplayMessages(messages).map((msg, index) => (
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
                            {
                                activeMode === "knowledge-graph" && (<PaperGraph />)
                            }
                        </div>

                        <CardFooter className="border-t border-slate-600/50 p-4 flex gap-2 items-end">
                            <textarea
                                placeholder="Ask me anything about scientific research... (Shift+Enter for new line)"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                className="flex-1 rounded-lg border border-gray-600 px-4 py-3 text-base bg-black text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none min-h-[48px] max-h-[200px]"
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                disabled={loading}
                                rows={1}
                                style={{
                                    overflowY: inputValue.split('\n').length > 3 ? 'auto' : 'hidden',
                                    height: 'auto'
                                }}
                                onInput={(e) => {
                                    const target = e.target as HTMLTextAreaElement;
                                    target.style.height = 'auto';
                                    target.style.height = Math.min(target.scrollHeight, 200) + 'px';
                                }}
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
