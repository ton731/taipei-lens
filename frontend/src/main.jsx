import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Filter out specific console error messages
const originalError = console.error;
console.error = (...args) => {
  const errorMessage = args[0];

  // Filter out React.Fragment warnings
  if (typeof errorMessage === 'string' &&
      errorMessage.includes('Invalid prop') &&
      errorMessage.includes('React.Fragment')) {
    return;
  }

  // Filter out empty Mapbox errors
  if (args[0] === 'Mapbox detailed error:' &&
      args[1]?.message === undefined) {
    return;
  }

  // Display other errors normally
  originalError.apply(console, args);
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
