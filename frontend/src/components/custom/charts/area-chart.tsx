import { TrendingUp } from "lucide-react";
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts";
import type { ChartConfig } from "@/components/ui/chart";
import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
} from "@/components/ui/chart";

const chartConfig = {
    count: {
        label: "Count",
        color: "var(--chart-1)",
    },
} satisfies ChartConfig;

interface ChartDataItem {
    year: string | number;
    count: number;
}

export function CustomAreaChart({
    title,
    description = "",
    chartData,
}: {
    title?: string;
    description?: string;
    chartData: ChartDataItem[];
}) {
    return (
        <div className="w-full h-full flex flex-col p-4">
            {/* Header */}
            <div className="flex flex-col gap-1 pb-4 mb-4">
                {title && <h3 className="text-lg font-semibold">{title}</h3>}
                {description && (
                    <p className="text-sm text-muted-foreground">{description}</p>
                )}
            </div>

            {/* Chart */}
            <div className="flex-1 flex items-center justify-center min-h-0">
                <ChartContainer config={chartConfig} className="h-[250px] w-full">
                    <AreaChart
                        data={chartData}
                        margin={{ left: 12, right: 12 }}
                    >
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis
                            dataKey="year"
                            tickLine={false}
                            axisLine={false}
                            tickMargin={8}
                            tickFormatter={(value) => String(value).slice(0, 4)}
                        />
                        <ChartTooltip
                            cursor={false}
                            content={<ChartTooltipContent indicator="area" />}
                        />
                        <Area
                            dataKey="count"
                            type="natural"
                            fill="var(--chart-1)"
                            fillOpacity={0.4}
                            stroke="var(--chart-1)"
                        />
                    </AreaChart>
                </ChartContainer>
            </div>

            {/* Footer */}
            <div className="flex w-full items-start gap-2 text-sm pt-4">
                <div className="grid gap-2">
                    <div className="flex items-center gap-2 leading-none font-medium">
                        Trending up by 5.2% this month <TrendingUp className="h-4 w-4" />
                    </div>
                    <div className="text-muted-foreground flex items-center gap-2 leading-none">
                        January - June 2024
                    </div>
                </div>
            </div>
        </div>
    );
}
