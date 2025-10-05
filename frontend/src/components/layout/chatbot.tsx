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

// Template responses for each mode
const modeResponses = {
    "inquiry-agent": [
        "I can help you search for information from the scientific research database.",
        "Feel free to ask questions about any scientific topic, and I'll find related papers for you.",
        "I will analyze and synthesize information from research studies to answer your questions.",
        "What research field would you like to explore? I can provide detailed information."
    ],
    "knowledge-graph": [
        "I can create relationships between scientific concepts in the database.",
        "Ask me about connections between authors, research topics, or publications.",
        "I will display the network of studies and authors related to your topic of interest.",
        "What topic would you like to explore through the knowledge network?"
    ],
    "hypo-agent": [
        "Initiating deep research session on topic: antibody repertoire sequencing and immune modeling...",
        "Searching PubMed Central and NASA Taskbook for related PMCID entries...",
        "Found 3 relevant papers for topic 'antibody repertoire sequencing'.",
        "Reading paper PMC5761896 — naive murine antibody repertoire using unamplified high-throughput sequencing...",
        "Reading paper PMC8534217 — transfer learning for antibody structure prediction and generative design...",
        "Reading paper PMC9982045 — AI-driven discovery of broadly neutralizing antibodies using protein language models...",
        "Synthesizing insights across 3 papers... detecting link between legacy murine repertoire data and modern AI antibody generation frameworks...",
        "Considering feasibility of integrating unamplified repertoire datasets with generative protein language models (ESM, ProtT5)...",
        "Evaluating human impact potential through AI-accelerated vaccine and therapeutic antibody discovery...",
        "Generating new hypothesis based on immunogenomic data revival and cross-domain AI reasoning...",
        "New hypothesis formulated successfully based on multi-paper synthesis.",
        "Deep research synthesis completed — new actionable hypothesis proposed from immunogenomic legacy data."
    ],
    "invent-agent": [
        "Initiating deep research session on topic: antibody repertoire sequencing and immune modeling...",
        "Searching PubMed Central and NASA Taskbook for related PMCID entries...",
        "Found 3 relevant papers for topic 'antibody repertoire sequencing'.",
        "Reading paper PMC5761896 — naive murine antibody repertoire using unamplified high-throughput sequencing...",
        "Reading paper PMC8534217 — transfer learning for antibody structure prediction and generative design...",
        "Reading paper PMC9982045 — AI-driven discovery of broadly neutralizing antibodies using protein language models...",
        "Synthesizing insights across 3 papers... detecting link between legacy murine repertoire data and modern AI antibody generation frameworks...",
        "Considering feasibility of integrating unamplified repertoire datasets with generative protein language models (ESM, ProtT5)...",
        "Evaluating human impact potential through AI-accelerated vaccine and therapeutic antibody discovery...",
        "Generating new hypothesis based on immunogenomic data revival and cross-domain AI reasoning...",
        "New hypothesis formulated successfully based on multi-paper synthesis.",
        "Deep research completed — AI-generated hypothesis successfully derived from immunogenomic legacy study PMC5761896."
    ]
};

export function Chatbot() {
    const [activeMode, setActiveMode] = useState("inquiry-agent");
    const [messages, setMessages] = useState<{ text: string; sender: "user" | "bot" }[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setOpen(true), 500);
        return () => clearTimeout(timer);
    }, []);

    // Reset messages khi chuyển đổi mode
    useEffect(() => {
        setMessages([]);
    }, [activeMode]);

    const callApi = async (prompt: string) => {
        setLoading(true);
        return new Promise<string>((resolve) => {
            setTimeout(() => {
                // Lấy random response từ mode hiện tại
                const responses = modeResponses[activeMode as keyof typeof modeResponses];
                const randomResponse = responses[Math.floor(Math.random() * responses.length)];
                resolve(`${randomResponse}\n\n[Phản hồi cho: "${prompt}"]`);
            }, 1000 + Math.random() * 1000);
        }).finally(() => setLoading(false));
    };

    const handleSend = async () => {
        if (!inputValue.trim()) return;
        const userMessage = inputValue;
        setMessages([...messages, { text: userMessage, sender: "user" }]);
        setInputValue("");

        const botResponse = await callApi(userMessage);
        setMessages((prev) => [...prev, { text: botResponse, sender: "bot" }]);
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
                            <h2 className="text-sm font-semibold text-white">Choose the Agent Mode</h2>
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

                        <div className="flex-1 px-4 py-1 overflow-y-auto text-white flex flex-col gap-2 scrollbar-thin scrollbar-thumb-gray-500 scrollbar-track-gray-900">
                            {messages.length === 0 && (
                                <div className="text-gray-400 italic text-xs space-y-2">
                                    <p>Welcome to the GoK Super Agent!</p>
                                </div>
                            )}
                            {messages.map((msg, index) => (
                                <div
                                    key={index}
                                    className={`p-2 rounded-md max-w-[80%] text-xs ${msg.sender === "user"
                                        ? "self-end bg-blue-600 text-white"
                                        : "self-start bg-gray-700 text-white"
                                        }`}
                                >
                                    {msg.text}
                                </div>
                            ))}
                            {loading && (
                                <p className="self-start text-gray-400 italic text-xs">Bot is thinking...</p>
                            )}
                            {
                                activeMode === "pro-agent" && (<PaperGraph />)
                            }
                        </div>

                        <CardFooter className="border-t border-slate-600/50 p-3 flex gap-2">
                            <Input
                                type="text"
                                placeholder="Welcome to the GoK! Ask me anything..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                className="flex-1 rounded-md border border-gray-600 px-3 py-2 text-sm bg-black text-white placeholder-gray-400 focus:outline-none focus:border-gray-500"
                                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                                disabled={loading}
                            />
                            <Button variant="secondary" size="sm" onClick={handleSend} disabled={loading}>
                                Send
                            </Button>
                        </CardFooter>
                    </Card>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
