import { Suspense, lazy } from "react";
import { useGlobal } from "@/context/GlobalContext";

const InsightButton = lazy(() => import("@/components/layout/insight-button"));
const HelpButton = lazy(() => import("@/components/layout/help-button"));
const SearchBar = lazy(() => import("@/components/layout/search-bar"));
const PaperDetail = lazy(() => import("@/components/layout/paper-detail"));
const Chatbot = lazy(() => import("@/components/layout/chatbot"));
const ESCButton = lazy(() => import("@/components/layout/esc-button"));
const TestComponent = lazy(() => import("./Test"));

export default function Home() {
  const { chatView } = useGlobal();

  return (
    <div className="relative min-h-screen min-w-screen flex items-center justify-center bg-neutral-950 text-neutral-100">
      <div className="fixed top-4 left-4 select-none z-10">
        <p className="text-xl font-semibold tracking-tight">
          <span className="text-green-400">Soft</span>
          <span className="text-white">AI</span>
        </p>
      </div>

      <Suspense fallback={null}>
        {!chatView ? (
          <>
            <div className="fixed top-4 right-4 z-10">
              <InsightButton />
            </div>

            <div className="fixed top-4 left-1/2 -translate-x-1/2 z-10">
              <SearchBar />
            </div>

            <div className="fixed bottom-4 right-4 z-10">
              <HelpButton />
            </div>
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

        <div className="z-5">
          <TestComponent />
        </div>
      </Suspense>
    </div>
  );
}
