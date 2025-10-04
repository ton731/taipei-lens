import React, { useState, useEffect } from 'react'
import MapComponent from './MapComponent'
import ChatBot from './components/ChatBot'
import './App.css'
import { jwtManager } from './lib/jwtManager'

function App() {
  // 提升 hoverInfo 到 App 層級，讓 ChatBot 和 MapComponent 都可以清除它
  const [hoverInfo, setHoverInfo] = useState(null)

  // LLM highlight areas state
  const [llmHighlightAreas, setLlmHighlightAreas] = useState(null)

  // 初始化 JWT token（應用啟動時）
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        console.log('[App] Initializing JWT authentication...');
        await jwtManager.getValidAccessToken();
        console.log('[App] JWT authentication initialized successfully');
      } catch (error) {
        console.error('[App] Failed to initialize JWT:', error);
      }
    };

    initializeAuth();
  }, [])

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
