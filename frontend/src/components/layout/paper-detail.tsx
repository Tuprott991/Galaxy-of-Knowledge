import { useEffect, useState, useRef } from "react";
import DOMPurify from "dompurify";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useGlobal } from "@/context/GlobalContext";
import { motion, AnimatePresence } from "framer-motion";
import { axiosClient } from "@/api/axiosClient.ts";

export default function PaperDetail() {
    const [cleanHTML, setCleanHTML] = useState("");
    const { selectedPaperId } = useGlobal();
    const [paperTitle, setPaperTitle] = useState<string>("");
    const [paperAuthors, setPaperAuthors] = useState<string>("");

    const [width, setWidth] = useState(750); // 👉 mặc định 750px
    const isResizing = useRef(false);

    useEffect(() => {
        if (!selectedPaperId) return;

        axiosClient.get(`/v1/papers/${selectedPaperId}/html-context`).then((res) => {
            const title = res.data?.data?.title || res.data?.title || "";
            const authorsArray = res.data?.data?.authors || res.data?.authors || [];
            const authors =
                Array.isArray(authorsArray) && authorsArray.length > 0
                    ? authorsArray.join(", ")
                    : "";

            let html = res.data?.data?.html_context ?? res.data?.html_context ?? "";

            // In đậm các phần chính
            html = html.replace(
                /\b(ABSTRACT|INTRODUCTION|METHODS|RESULTS|DISCUSSION|CONCLUSION|ANNOUNCEMENT|TABLE\s*\d*)\b/g,
                '<h2 style="font-weight:bold; color:black; margin-top:1.5em;">$1</h2>'
            );

            setPaperTitle(title);
            setPaperAuthors(authors);
            setCleanHTML(DOMPurify.sanitize(html));
        });
    }, [selectedPaperId]);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing.current) return;
            setWidth(Math.min(Math.max(500, e.clientX - 20), 1200));
        };

        const handleMouseUp = () => {
            isResizing.current = false;
            document.body.style.cursor = "default";
        };

        window.addEventListener("mousemove", handleMouseMove);
        window.addEventListener("mouseup", handleMouseUp);

        return () => {
            window.removeEventListener("mousemove", handleMouseMove);
            window.removeEventListener("mouseup", handleMouseUp);
        };
    }, []);

    const startResizing = () => {
        isResizing.current = true;
        document.body.style.cursor = "ew-resize";
    };

    return (
        <AnimatePresence>
            {cleanHTML && (
                <motion.div
                    initial={{ x: "-100%", opacity: 0 }}
                    animate={{ x: 30, y: -10, opacity: 1 }}
                    exit={{ x: "-100%", opacity: 0 }}
                    transition={{ duration: 0.5, ease: "easeInOut" }}
                    className="fixed top-0 left-0 h-full z-50 flex items-center"
                >
                    <div
                        className="relative h-[90%]"
                        style={{ width: `${width}px` }}
                    >
                        {/* Card chính */}
                        <Card className="mx-0 h-full shadow-2xl rounded-lg bg-white border border-gray-200">
                            <CardHeader className="py-3 px-6 border-b border-gray-300">
                                <h2 className="text-lg font-semibold text-black mb-1">{paperTitle}</h2>
                                {paperAuthors && (
                                    <p className="text-sm text-gray-600 italic">{paperAuthors}</p>
                                )}
                            </CardHeader>

                            <CardContent className="overflow-auto h-full p-6">
                                <div
                                    className="
                    prose max-w-full text-justify
                    prose-p:leading-relaxed
                    [&_h2]:font-bold [&_h2]:text-black [&_h2]:mt-6 [&_h2]:mb-3
                    [&_strong]:font-semibold
                  "
                                    dangerouslySetInnerHTML={{ __html: cleanHTML }}
                                />
                            </CardContent>
                        </Card>

                        {/* Thanh kéo giãn */}
                        <div
                            onMouseDown={startResizing}
                            className="absolute top-0 right-0 w-2 h-full cursor-ew-resize hover:bg-gray-300/50 rounded-r-lg"
                        />
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
