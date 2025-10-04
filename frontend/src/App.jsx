import React, { useState } from 'react'
import MapComponent from './MapComponent'
import ChatBot from './components/ChatBot'
import './App.css'

function App() {
  // 提升 hoverInfo 到 App 層級，讓 ChatBot 和 MapComponent 都可以清除它
  const [hoverInfo, setHoverInfo] = useState(null)

  // LLM highlight areas state
  const [llmHighlightAreas, setLlmHighlightAreas] = useState(null)

  // 清除 AI highlight 的函數
  const clearLlmHighlight = () => {
    setLlmHighlightAreas(null)
  }

  return (
    <div className="App">
      <MapComponent
        hoverInfo={hoverInfo}
        setHoverInfo={setHoverInfo}
        llmHighlightAreas={llmHighlightAreas}
        clearLlmHighlight={clearLlmHighlight}
      />
      <ChatBot
        onMouseEnter={() => setHoverInfo(null)}
        onHighlightAreas={setLlmHighlightAreas}
      />
    </div>
  )
}

export default App
