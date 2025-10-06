import {Suspense, lazy, useState} from "react";
import { useGlobal } from "@/context/GlobalContext";
import TestComponent from "./Test";
import FilterSlider from "@/components/layout/Filter-Slider.tsx";

const InsightButton = lazy(() => import("@/components/layout/insight-button").then(m => ({ default: m.InsightButton })));
const HelpButton = lazy(() => import("@/components/layout/help-button").then(m => ({ default: m.HelpButton })));
const SearchBar = lazy(() => import("@/components/layout/search-bar").then(m => ({ default: m.SearchBar })));
const PaperDetail = lazy(() => import("@/components/layout/paper-detail").then(m => ({ default: m.PaperDetail })));
const Chatbot = lazy(() => import("@/components/layout/chatbot").then(m => ({ default: m.Chatbot })));
const ESCButton = lazy(() => import("@/components/layout/esc-button").then(m => ({ default: m.ESCButton })));

export default function Home() {
  const { chatView } = useGlobal();
    const [scoreThreshold, setScoreThreshold] = useState(0);


    return (
    <div className="relative min-h-screen min-w-screen flex items-center justify-center bg-neutral-950 text-neutral-100">
      <Suspense fallback={null}>
        {!chatView ? (
          <>
            <div className="fixed top-4 left-4 select-none z-10">
              <p className="text-xl font-semibold tracking-tight">
                <span className="text-green-400">Soft</span>
                <span className="text-white">AI</span>
              </p>
            </div>

            <div className="fixed top-4 right-4 z-10">
              <InsightButton />
            </div>

            <div className="fixed top-4 left-1/2 -translate-x-1/2 z-10">
              <SearchBar />
            </div>

            <div className="fixed bottom-4 right-4 z-10">
              <HelpButton />
            </div>
              <FilterSlider value={scoreThreshold} onChange={setScoreThreshold} />

          </>
        ) : (
          <>
            <div className="fixed top-4 left-4 z-10">
              <PaperDetail />
            </div>

            <div className="fixed bottom-4 right-4 z-10">
              <Chatbot />
            </div>

            <div className="fixed bottom-4 left-4 z-10">
              <ESCButton />
            </div>
          </>
        )}
      </Suspense>

        <div className="z-5">
            <TestComponent scoreThreshold={scoreThreshold} />  {/* 👈 thêm dòng này */}
        </div>
    </div>
  );
}
