import type { Paper } from "@/types";

export function ShortDetail({ paper }: { paper: Paper }) {
    return (
        <div className="fixed top-14 p-[10px] max-w-100vw left-1/2 text-white -translate-x-1/2 z-10">
            <h3 className="font-bold text-xl text-center">{paper.title}</h3>
            <p className="flex justify-center font-mono text-base text-[#808080] font-semibold">{paper.cluster}</p>
            <div className="flex justify-center gap-1 mt-1 items-center">
                <span
                    className="font-semibold flex items-center bg-neutral-800/40 backdrop-blur-md border border-neutral-700 hover:bg-neutral-700/50 px-2 rounded-md justify-center text-xs font-mono"
                >
                    Space
                </span>
                <span className="text-sm font-semibold">Open</span>
            </div>
        </div>
    )
}