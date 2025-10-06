export default function FilterSlider({ value, onChange }: { value: number; onChange: (v: number) => void }) {
    return (
        <div className="fixed bottom-4 left-4 z-20 flex flex-col items-center bg-neutral-900/70 p-3 rounded-xl shadow-lg backdrop-blur">
            <label className="text-sm mb-2 text-neutral-300 select-none">Score ≥ {value}</label>
            <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                className="w-32 accent-green-400 cursor-pointer"
            />
        </div>
    );
}
