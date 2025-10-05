import React, { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import {Card, CardContent, CardHeader} from "@/components/ui/card";
import { useGlobal } from "@/context/GlobalContext";
import { motion, AnimatePresence } from "framer-motion";
import {axiosClient} from "@/api/axiosClient.ts";

export const PaperDetail: React.FC = () => {
    const [cleanHTML, setCleanHTML] = useState("");
    const { htmlContent, selectedPaperId } = useGlobal();
    const [paperTitle, setPaperTitle] = useState<string>("");

    useEffect(() => {
        if (!selectedPaperId) return;

        axiosClient.get(`/v1/papers/${selectedPaperId}/html-context`).then((res) => {
            setPaperTitle(res.data.title);
            setCleanHTML(DOMPurify.sanitize(res.data.html_context ?? ""));
        });
    }, [selectedPaperId]);

    return (
        <AnimatePresence>
            {htmlContent && (
                <motion.div
                    initial={{ x: "-100%", opacity: 0 }}
                    animate={{ x: 30, y: -10, opacity: 1 }}
                    exit={{ x: "-100%", opacity: 0 }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                    className="fixed top-0 left-0 h-full z-50 flex items-center"
                >
                    <Card className="mx-0 w-[700px] h-[90%] shadow-2xl rounded-lg">
                        <CardHeader className="flex justify-between items-center py-2 px-4 border-b border-slate-600/50">
                            <h2 className="text-lg font-semibold text-black">
                                {paperTitle}
                            </h2>
                        </CardHeader>
                        <CardContent className="overflow-auto h-full p-6">
                            <div
                                className="prose max-w-full text-justify"
                                dangerouslySetInnerHTML={{ __html: cleanHTML }}
                            />
                        </CardContent>

                    </Card>
                </motion.div>
            )}
        </AnimatePresence>
    );
};
