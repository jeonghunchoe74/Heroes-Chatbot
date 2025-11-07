// 실행 방법:
// 1. 패키지 설치: npm install recharts
// 2. 클라이언트 실행: npm run dev 


import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Chatbot from './Chatbot'
import Chart from './Chart'

function App() {
  const [activeComponent, setActiveComponent] = useState(null);

  return (
    <>
      {activeComponent === null && (
        <div style={{ marginBottom: 20 }}>
          <button onClick={() => setActiveComponent('Chatbot')}>챗봇</button>
          <button onClick={() => setActiveComponent('Chart')}>차트</button>
        </div>
      )}

      <div>
        {activeComponent === 'Chatbot' && (
          <Chatbot onBack={() => setActiveComponent(null)} />
        )}
        {activeComponent === 'Chart' && (
          <Chart onBack={() => setActiveComponent(null)} />
        )}
      </div>
    </>
  );
}

export default App
