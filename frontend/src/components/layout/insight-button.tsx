import { useState, lazy, Suspense } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { axiosClient } from "@/api/axiosClient";

const CustomAreaChart = lazy(() =>
  import("@/components/custom/charts").then((mod) => ({
    default: mod.CustomAreaChart,
  }))
);

export function InsightButton() {
  const [yearlyTrends, setYearlyTrends] = useState<any[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleViewInsightClick = async () => {
    if (yearlyTrends) return;
    setIsLoading(true);
    try {
      const res = await axiosClient.get("/v1/stats/trends/yearly");
      setYearlyTrends(res.data.yearly_trends);
    } catch (error) {
      console.error("Error fetching yearly trends:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="secondary"
          className="flex items-center gap-2 bg-neutral-800/40 backdrop-blur-md border border-neutral-700 hover:bg-neutral-700/50"
          onClick={handleViewInsightClick}
        >
          Insight
        </Button>
      </DialogTrigger>

      <DialogContent className="min-w-[90vw] bg-neutral-900/80 backdrop-blur-xl border border-neutral-700 text-neutral-100 rounded-2xl shadow-2xl">
        <DialogTitle>Insights Overview</DialogTitle>
        <DialogDescription>
          Explore yearly paper publication trends
        </DialogDescription>

        {isLoading ? (
          <div className="text-center py-8 text-neutral-400">Loading...</div>
        ) : (
          <Suspense fallback={null}>
            <CustomAreaChart
              title="Number of Papers by Year"
              description="This chart shows the total number of published papers for each year"
              chartData={yearlyTrends || []}
            />
          </Suspense>
        )}
      </DialogContent>
    </Dialog>
  );
}
