import React, { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { Card, CardContent } from "@/components/ui/card";

import { htmlContent } from "@/data/paper-detail";

export const PaperDetail: React.FC = () => {
    const [cleanHTML, setCleanHTML] = useState("");

    useEffect(() => {
        setCleanHTML(DOMPurify.sanitize(htmlContent));
    }, []);

    return (
        <Card className="mx-0 max-w-xl w-full">
            <CardContent className="overflow-auto max-h-[70vh]">
                <div
                    className="prose max-w-full text-justify"
                    dangerouslySetInnerHTML={{ __html: cleanHTML }}
                />
            </CardContent>
        </Card>
    );
};
