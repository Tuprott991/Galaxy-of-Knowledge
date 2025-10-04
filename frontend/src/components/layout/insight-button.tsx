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

export function InsightButton() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="secondary"
          className="flex items-center gap-2 bg-neutral-800/40 backdrop-blur-md border border-neutral-700 hover:bg-neutral-700/50"
        >
          Insight
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-xl bg-neutral-900/80 backdrop-blur-xl border border-neutral-700 text-neutral-100 rounded-2xl shadow-2xl">
        <DialogHeader className="text-center space-y-1">
          <DialogTitle className="text-lg font-semibold">Insight View</DialogTitle>
          <Separator className="bg-neutral-700" />
        </DialogHeader>
        <DialogDescription className="mt-1 space-y-2 text-lg">

        </DialogDescription>
      </DialogContent>
    </Dialog>
  );
}
