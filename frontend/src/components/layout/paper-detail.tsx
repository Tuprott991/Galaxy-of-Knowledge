import React from "react";
import { Card, CardContent } from "@/components/ui/card";

import { paperDetail } from "@/data/paper-detail";

export const PaperDetail: React.FC = () => {
    return (
        <Card className="w-full mx-0">
            <CardContent>
                <div
                    className="text-gray-700 max-h-110 overflow-y-auto"
                    dangerouslySetInnerHTML={{ __html: paperDetail }}
                />
            </CardContent>
        </Card>
    );
};
