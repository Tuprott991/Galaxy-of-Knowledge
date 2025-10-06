import { useEffect } from 'react';

export default function FilterSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
    const handleDecrease = () => {
        if (value > 0) onChange(value - 1);
    };

    const handleIncrease = () => {
        if (value < 100) onChange(value + 1);
    };

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === '-' || e.key === '_') {
                e.preventDefault();
                if (value > 0) onChange(value - 1);
            } else if (e.key === '+' || e.key === '=') {
                e.preventDefault();
                if (value < 100) onChange(value + 1);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [value, onChange]);

    return (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 bg-neutral-900/80 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md border border-neutral-700/50">
            <button
                onClick={handleDecrease}
                className="w-8 h-8 flex items-center justify-center bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg transition-colors text-lg font-bold"
                aria-label="Decrease score"
            >
                −
            </button>
            
            <div className="flex flex-col items-center gap-1">
                <label className="text-sm font-medium text-neutral-200 select-none whitespace-nowrap">
                    Score ≥ {value}
                </label>
                <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={value}
                    onChange={(e) => onChange(Number(e.target.value))}
                    className="w-48 h-2 accent-green-400 cursor-pointer"
                />
            </div>

            <button
                onClick={handleIncrease}
                className="w-8 h-8 flex items-center justify-center bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg transition-colors text-lg font-bold"
                aria-label="Increase score"
            >
                +
            </button>
        </div>
    );
}