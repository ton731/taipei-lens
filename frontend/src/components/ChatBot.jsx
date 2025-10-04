import React, { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import './ChatBot.css'

// 預設問題列表
const SAMPLE_QUESTIONS = [
  '台北市人口數量最高的前三個行政區在哪裡？',
  '高齡人口比例超過 20% 且平均建築屋齡超過 40 年的行政區在哪裡？',
  '哪一個行政區的高齡獨居人口數最多？',
  '低收入戶比例最高的行政區有哪些？',
  '高齡人口比例最高的行政區在哪裡？',
  '哪個行政區的總人口最多？',
  '平均建築屋齡最年輕的前三個行政區有哪些？',
  '總人口超過 20 萬的行政區有哪些？',
  '高齡人口比例超過 25% 的行政區在哪裡？',
  '台北市都市更新的主要目標是什麼？',
  '什麼是容積獎勵制度？',
  '台北市有哪些著名的都市更新案例？',
  '整建維護和重建有什麼不同？',
  '什麼是危老重建條例？',
  '都市更新可以獲得哪些容積獎勵？',
  '台北市推動都市韌性規劃的原因是什麼？'
]

function ChatBot({ onMouseEnter, onHighlightAreas }) {
  const [isFocused, setIsFocused] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [showResponse, setShowResponse] = useState(false)
  const [aiResponse, setAiResponse] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [userQuestion, setUserQuestion] = useState('')
  const inputRef = useRef(null)

  const hasContent = inputValue.trim().length > 0

  // 隨機選擇問題的函數
  const handleRandomQuestion = () => {
    const randomIndex = Math.floor(Math.random() * SAMPLE_QUESTIONS.length)
    setInputValue(SAMPLE_QUESTIONS[randomIndex])
    // 點擊骰子後自動 focus input，觸發 focused 狀態
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }

  const handleSubmit = async () => {
    if (hasContent && !isLoading) {
      const question = inputValue

      // 保存用戶問題並開始 Loading（不清空輸入框）
      setUserQuestion(question)
      setIsLoading(true)

      try {
        // 調用後端 API
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
        const response = await fetch(`${apiBaseUrl}/llm/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: question
          })
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'API request failed')
        }

        const data = await response.json()
        setAiResponse(data.answer)
        setShowResponse(true)

        // 處理 highlight areas（如果有的話）
        if (data.highlight_areas && onHighlightAreas) {
          console.log('Received highlight areas from LLM:', data.highlight_areas)
          onHighlightAreas(data.highlight_areas)
        } else if (onHighlightAreas) {
          // 如果沒有 highlight areas，清除之前的 highlight
          onHighlightAreas(null)
        }

        // 收到回應後才清空輸入框
        setInputValue('')
      } catch (error) {
        console.error('Error calling LLM API:', error)
        setAiResponse(`抱歉，發生錯誤：${error.message}\n\n請確認後端服務正在運行，且 OPENAI_API_KEY 已正確設定。`)
        setShowResponse(true)
        // 即使出錯也清空輸入框
        setInputValue('')
      } finally {
        setIsLoading(false)
      }
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && hasContent) {
      handleSubmit()
    }
  }

  const handleCloseResponse = () => {
    setShowResponse(false)
    // 清除地圖上的 AI highlight
    if (onHighlightAreas) {
      onHighlightAreas(null)
    }
  }

  return (
    <div className="chatbot-container" onMouseEnter={onMouseEnter}>
      {showResponse && (
        <div className="chatbot-response-popup">
          <button className="chatbot-response-close" onClick={handleCloseResponse}>
            ✕
          </button>
          <div className="chatbot-response-content">
            {userQuestion && (
              <div className="chatbot-user-question">
                <strong>問題：</strong>{userQuestion}
              </div>
            )}
            <ReactMarkdown>{aiResponse}</ReactMarkdown>
          </div>
        </div>
      )}
      <div className={`chatbot-input-wrapper ${isFocused ? 'focused' : ''}`}>
        <input
          ref={inputRef}
          type="text"
          className="chatbot-input"
          placeholder="Ask a question about Taipei..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyPress={handleKeyPress}
        />
        <button
          className="chatbot-dice-button"
          onClick={handleRandomQuestion}
          onMouseDown={(e) => e.preventDefault()}
          title="隨機選擇一個問題"
          disabled={isLoading}
        >
          🎲
        </button>
        <button
          className={`chatbot-submit-button ${hasContent || isLoading ? 'active' : ''} ${isLoading ? 'loading' : ''}`}
          onClick={handleSubmit}
          disabled={!hasContent && !isLoading}
        >
          {isLoading ? (
            <div className="chatbot-spinner"></div>
          ) : (
            <span style={{ fontSize: '1.2em' }}>⬆</span>
          )}
        </button>
      </div>
    </div>
  )
}

export default ChatBot
