import type { Paper } from "@/types";

export function ShortDetail({ paper }: { paper: Paper }) {
    return (
        <div className="fixed top-14 left-1/2 -translate-x-1/2 z-10 p-3 max-w-[90vw] text-white">
            {/* Topic */}
            {paper.topic && (
                <div className="flex justify-center mb-1">
                    <span
                        className="px-3 py-[3px] rounded-full bg-neutral-800/60 border border-neutral-700 
                           backdrop-blur-md text-xs font-medium text-gray-200 
                           hover:bg-neutral-700/70 transition-colors duration-200"
                    >
                        {paper.topic}
                    </span>
                </div>
            )}

            {/* Title */}
            <h3 className="font-bold text-xl text-center leading-snug">{paper.title}</h3>

            {/* Cluster */}
            <p className="text-center font-mono text-sm text-gray-400 font-semibold mt-1">
                {paper.cluster}
            </p>

            {/* Action Button */}
            <div className="flex justify-center gap-1 mt-2 items-center">
                <button
                    className="flex items-center gap-1 px-2 py-[2px] bg-neutral-800/50 border border-neutral-700 
                       rounded-md font-mono text-xs text-gray-200 hover:bg-neutral-700/70 
                       transition-colors duration-200 backdrop-blur-md"
                >
                    <span className="font-bold text-yellow-400">Q</span>
                    <span className="text-sm font-semibold">Open</span>
                </button>
            </div>
        </div>
    );
}