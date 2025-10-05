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
} from "@/components/custom/charts";
import {
  axiosClient
} from "@/api/axiosClient";
import { useState } from "react";

export default function InsightButton() {
  const [yearlyTrends, setYearlyTrends] = useState(null);

  const handleViewInsightClick = async () => {
    try {
      const res = await axiosClient.get('/v1/stats/trends/yearly');
      const data = await res.data.yearly_trends;
      setYearlyTrends(data);
    } catch (error) {
      console.error("Error fetching yearly trends:", error);
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
        <DialogTitle></DialogTitle>
        <DialogDescription></DialogDescription>
        <CustomAreaChart
          title="Area Chart"
          description="Showing total visitors for the last 6 months"
          chartData={yearlyTrends || []}
        />
      </DialogContent >
    </Dialog >
  );
}
