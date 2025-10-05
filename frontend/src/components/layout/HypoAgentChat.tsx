import { useState } from "react";
import { Card, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";

export function HypoAgentChat() {
    const [messages, setMessages] = useState<{ text: string; sender: "user" | "bot" }[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [open] = useState(true);

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

    const handleSend = () => {
        if (!inputValue.trim()) return;

        setMessages([...messages, { text: inputValue, sender: "user" }, { text: hypoContent, sender: "bot" }]);
        setInputValue("");
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
                                <h2 className="text-sm font-semibold text-white">Hypo Agent Mode</h2>
                            </div>
                        </CardHeader>

                        <div className="flex-1 px-4 py-3 overflow-y-auto text-white flex flex-col gap-3 scrollbar-thin scrollbar-thumb-gray-500 scrollbar-track-gray-900">
                            {messages.length === 0 && (
                                <div className="text-gray-400 italic text-sm space-y-2 p-4">
                                    <p className="text-lg font-semibold">Hypo Agent Chat</p>
                                    <p>Send a message to see the hypothesis response.</p>
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
                        </div>

                        <CardFooter className="border-t border-slate-600/50 p-4 flex gap-2 items-end">
                            <textarea
                                placeholder="Ask about the hypothesis..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                className="flex-1 rounded-lg border border-gray-600 px-4 py-3 text-base bg-black text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none min-h-[48px] max-h-[200px]"
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
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
                                disabled={!inputValue.trim()}
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