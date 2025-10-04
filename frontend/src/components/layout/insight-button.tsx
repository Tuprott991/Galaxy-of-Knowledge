import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  CustomAreaChart,
  CustomPieChart,
  CustomRadarChart,
  CustomBarChart,
} from "@/components/custom/charts";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel"

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

      <DialogContent className="min-w-[90vw] bg-neutral-900/80 backdrop-blur-xl border border-neutral-700 text-neutral-100 rounded-2xl shadow-2xl">
        <DialogTitle></DialogTitle>
        <DialogDescription></DialogDescription>
        <Carousel>
          <CarouselContent>
            <CarouselItem>
              <div className="text-lg grid grid-cols-2 gap-4">
                <CustomAreaChart />
                <CustomPieChart />
              </div>
            </CarouselItem>
            <CarouselItem>
              <div className="text-lg grid grid-cols-2 gap-4">
                <CustomRadarChart />
                <CustomBarChart />
              </div>
            </CarouselItem>
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      </DialogContent>
    </Dialog >
  );
}
