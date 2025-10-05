import { useEffect } from "react";
import { useGlobal } from "@/context/GlobalContext";
import { Button } from "@/components/ui/button";

export default function ESCButton() {
    const { setChatView } = useGlobal();

    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
            setChatView(false);
        }
    };

    useEffect(() => {
        window.addEventListener("keydown", handleKeyDown);
    });

    return (
        <div className="flex gap-2 items-center">
            <Button
                variant="secondary"
                className="flex items-center gap-2 bg-neutral-800/40 backdrop-blur-md border border-neutral-700 cursor-none hover:bg-neutral-800/40"
            >
                Esc
            </Button>
            <small className="text-sm leading-none font-medium text-white">to Quit</small>
        </div>
    );
}