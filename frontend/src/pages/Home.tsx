import { InsightButton } from "@/components/layout/insight-button";
import { HelpButton } from "@/components/layout/help-button";
import { SearchBar } from "@/components/layout/search-bar";
import { PaperDetail } from "@/components/layout/paper-detail";
import { Chatbot } from "@/components/layout/chatbot";
import { ESCButton } from "@/components/layout/esc-button";
import { useGlobal } from "@/context/GlobalContext";
import TestComponent from "./Test"


export default function Home() {
  const { chatView } = useGlobal();

  return (
    <div className="relative min-h-screen min-w-screen flex items-center justify-center bg-neutral-950 text-neutral-100">
      {!chatView ? (
        <>
          {/* Logo góc trái */}
          <div className="fixed top-4 left-4 select-none z-10">
            <p className="text-xl font-semibold tracking-tight">
              <span className="text-green-400">Soft</span>
              <span className="text-white">AI</span>
            </p>
          </div>

          {/* Nút Insight góc phải */}
          <div className="fixed top-4 right-4 z-10">
            <InsightButton />
          </div>

          {/* Ô tìm kiếm trung tâm */}
          <div className="fixed top-4 left-1/2 -translate-x-1/2 z-10">
            <SearchBar />
          </div>

          {/* Nút Help góc phải dưới */}
          <div className="fixed bottom-4 right-4 z-10">
            <HelpButton />
          </div>

          <div className="z-5">
            <TestComponent></TestComponent>
          </div>
        </>
      ) : (
        <>
          <div className="flex w-[100vw] max-w-7xl gap-4 mx-4 items-center overflow-hidden h-100">
            {/* Left - 3 phần */}
            <div className="flex-[3] h-full">
              <PaperDetail />
            </div>

            {/* Middle - 1 phần */}
            <div className="flex-[1] h-full">
              <p>Hello Nhan Pham</p>
            </div>

            {/* Right - 2 phần */}
            <div className="flex-[2] h-full">
              <Chatbot />
            </div>
          </div>
          <div className="fixed bottom-4 left-4 z-10">
            <ESCButton />
          </div>
        </>
      )}
    </div>
  );
}
