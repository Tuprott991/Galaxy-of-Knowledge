import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { ControlItem } from "@/components/custom/list-item";
import { BadgeQuestionMark } from "lucide-react";

export function HelpButton() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="secondary"
          className="flex items-center gap-2 bg-neutral-800/40 backdrop-blur-md border border-neutral-700 hover:bg-neutral-700/50"
        >
          <BadgeQuestionMark size={20} />
          Help
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-sm bg-neutral-900/80 backdrop-blur-xl border border-neutral-700 text-neutral-100 rounded-2xl shadow-2xl">
        <DialogHeader className="text-center space-y-1">
          <DialogTitle className="text-lg font-semibold">
            Control Guide
          </DialogTitle>
          <Separator className="bg-neutral-700" />
        </DialogHeader>

        <DialogDescription className="mt-1 space-y-2 text-lg">
          <ControlItem listKeyText={["W", "S", "A", "D"]} desc="Move" />
          <ControlItem listKeyText={["Mouse"]} desc="Look Around" />
          <ControlItem listKeyText={["Click"]} desc="Activate Control Mode" />
          <ControlItem listKeyText={["ESC"]} desc="Exit Control Mode" />
        </DialogDescription>
      </DialogContent>
    </Dialog>
  );
}
