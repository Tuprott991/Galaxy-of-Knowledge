import { Badge } from "@/components/ui/badge";
import type { KeyType, ControlItemProps } from "@/types";

export function ControlItem({ listKeyText, desc }: ControlItemProps) {
  return (
    <div className="flex justify-between items-center">
      <div className="flex gap-3 px-2 py-1 rounded-md">
        {listKeyText.map((key: KeyType, index) => (
          <Badge
            key={index}
            variant="secondary"
            className="bg-gray-700/75 backdrop-blur text-white font-mono px-2 py-1 text-sm"
          >
            {key}
          </Badge>
        ))}
      </div>
      {desc && <span className="text-neutral-300 text-base">{desc}</span>}
    </div>
  );
}
