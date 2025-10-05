import type { Paper } from "@/types";

export default function ShortDetail({ paper }: { paper: Paper }) {
    return (
        <div className="fixed top-14 p-2 max-w-full left-1/2 text-white -translate-x-1/2 z-10">
            <div className="flex justify-center gap-1 mt-1 items-center">
                <span className="flex justify-center mb-1 gap-1 flex-wrap text-sm text-[#808080] border
                border-neutral-700/50 px-2 py-1 rounded-md">
                    {paper.topic}
                </span>
            </div>

            <h3 className="font-bold text-xl text-center">{paper.title}</h3>

            <p className="flex justify-center font-mono text-base text-[#808080] font-semibold">
                {paper.cluster}
            </p>

            <div className="flex justify-center gap-1 mt-1 items-center">
                <span className="font-semibold flex items-center bg-neutral-800/40 backdrop-blur-md border border-neutral-700 hover:bg-neutral-700/50 px-2 rounded-md justify-center text-xs font-mono">
                    Q
                </span>
                <span className="text-sm font-semibold">Open</span>
            </div>
        </div>
    );
}
