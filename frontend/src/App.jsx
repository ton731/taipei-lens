import React, { useState } from 'react'
import MapComponent from './MapComponent'
import ChatBot from './components/ChatBot'
import './App.css'

function App() {
  // Lift hoverInfo to App level so both ChatBot and MapComponent can clear it
  const [hoverInfo, setHoverInfo] = useState(null)

  // LLM highlight areas state
  const [llmHighlightAreas, setLlmHighlightAreas] = useState(null)

  // Function to clear AI highlight
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
