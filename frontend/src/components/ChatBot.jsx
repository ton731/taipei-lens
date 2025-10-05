import React, { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { getFormattedContactInfo } from '../constants/contactInfo'
import './ChatBot.css'

// Sample questions list
const SAMPLE_QUESTIONS = [
  // Population and demographics
  'Top 3 districts by population?',
  'Districts with elderly ratio >20% and building age >40 years?',
  'District with most elderly living alone?',
  'Districts with highest low-income ratio?',
  'District with highest elderly ratio?',
  'District with largest population?',
  'Top 3 districts with newest buildings?',
  'Districts with population over 200k?',
  'Districts with elderly ratio >25%?',
  
  // Climate and environmental features
  'Which district has the highest land surface temperature?',
  'Top 5 districts with lowest vegetation coverage?',
  'Which district has the coolest temperatures?',
  'Districts with highest nighttime light intensity?',
  
  // Risk assessment features  
  'District with highest earthquake building fragility risk?',
  'Districts with highest seismic vulnerability?',
  
  // Infrastructure and coverage
  'Districts with full park coverage within 300m?',
  'Districts lacking green space accessibility?',
  
  // Multi-criteria analysis
  'Hot districts with low vegetation and high population density?',
  'Districts needing urgent green infrastructure: low NDVI + high LST?',
  
  // Urban planning knowledge
  'Main goals of Taipei urban renewal?',
  'What is floor area ratio incentive?',
  'Notable urban renewal cases in Taipei?',
  'Difference between renovation and reconstruction?',
  'What is the dangerous buildings ordinance?',
  'Urban renewal FAR incentives?',
  'Why promote urban resilience in Taipei?',
  
  // Platform information
  'Who made this?'
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

  // Function to select random question
  const handleRandomQuestion = () => {
    const randomIndex = Math.floor(Math.random() * SAMPLE_QUESTIONS.length)
    setInputValue(SAMPLE_QUESTIONS[randomIndex])
    // Auto focus input after clicking dice button to trigger focused state
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }

  const handleSubmit = async () => {
    if (hasContent && !isLoading) {
      const question = inputValue

      // Save user question and start loading (don't clear input)
      setUserQuestion(question)
      setIsLoading(true)

      try {
        // Call backend API
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
        
        // Check if response contains contact info trigger
        let finalResponse = data.answer
        if (finalResponse && finalResponse.includes('SHOW_CONTACT_INFO')) {
          finalResponse = getFormattedContactInfo()
        }
        
        setAiResponse(finalResponse)
        setShowResponse(true)

        // Handle highlight areas (if available)
        if (data.highlight_areas && onHighlightAreas) {
          console.log('Received highlight areas from LLM:', data.highlight_areas)
          onHighlightAreas(data.highlight_areas)
        } else if (onHighlightAreas) {
          // Clear previous highlights if no highlight areas
          onHighlightAreas(null)
        }

        // Clear input after receiving response
        setInputValue('')
      } catch (error) {
        console.error('Error calling LLM API:', error)
        setAiResponse(`Sorry, an error occurred: ${error.message}\n\nPlease confirm that the backend service is running and OPENAI_API_KEY is properly configured.`)
        setShowResponse(true)
        // Clear input even if error occurs
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
    // Clear AI highlights on map
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
                <strong>Question: </strong>{userQuestion}
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
          title="Choose a random question"
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
