import {
    Card,
    CardContent,
    CardFooter,
    CardHeader,
} from "@/components/ui/card"
import { useState } from "react"
import { Button } from "@/components/ui/button"

export function Chatbot() {
    const [messages] = useState([
        { id: 1, sender: "user", text: "Rephrase ‘This is an ai chatbot generated for better communication and simpler work flows’" },
        { id: 2, sender: "bot", text: "This AI chatbot has been developed to optimize communication and simplify work processes, ultimately leading to smoother operations." },
    ])

    // tab hiện tại
    const [activeTab, setActiveTab] = useState("Chat")

    const tabs = ["Chat", "Graph", "Hypo", "Inven"]

    return (
        <Card className="w-[400px] h-[600px] flex flex-col bg-black border border-white rounded-xl">
            {/* Header với 4 nút */}
            <CardHeader className="flex justify-center border-b border-white px-3 py-2">
                <div className="flex gap-3">
                    {tabs.map((tab) => (
                        <Button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            variant="outline"
                            size="sm"
                            className={`w-18 h-10 rounded-md px-3 py-2 text-sm ${
                                activeTab === tab
                                    ? "bg-gray-500 text-white border-gray-500"
                                    : "bg-transparent text-white border-white hover:bg-gray-700"
                            }`}
                        >
                            {tab}
                        </Button>
                    ))}
                </div>
            </CardHeader>

            {/* Nội dung chat */}
            <CardContent className="flex-1 overflow-y-auto space-y-3 p-3">
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex ${
                            msg.sender === "user" ? "justify-end" : "justify-start"
                        }`}
                    >
                        <div
                            className={`rounded-xl px-3 py-2 max-w-[75%] text-sm ${
                                msg.sender === "user"
                                    ? "bg-gray-700 text-white"
                                    : "bg-gray-200 text-black"
                            }`}
                        >
                            {msg.text}
                        </div>
                    </div>
                ))}
            </CardContent>

            {/* Input */}
            <CardFooter className="border-t border-white p-3 flex gap-2">
                <input
                    type="text"
                    placeholder="Type a message..."
                    className="flex-1 rounded-md border border-gray-400 px-3 py-2 text-sm bg-black text-white placeholder-gray-400"
                />
            </CardFooter>
        </Card>
    )
}
