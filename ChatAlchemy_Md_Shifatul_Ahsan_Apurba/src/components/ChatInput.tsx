import React, { useState, useEffect, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  darkMode?: boolean;
}

export function ChatInput({ onSend, disabled, darkMode = false }: ChatInputProps) {
  const [input, setInput] = useState('');

  useEffect(() => {
    const handleQuestionClick = (event: any) => {
      const question = event.detail.question;
      setInput(question);
    };

    window.addEventListener('question-click', handleQuestionClick);
    return () => window.removeEventListener('question-click', handleQuestionClick);
  }, []);

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={`border-t ${darkMode ? 'bg-gray-800/90 border-gray-700' : 'bg-white/80 border-gray-200'} backdrop-blur-sm`}>
      <div className="max-w-[95%] mx-auto p-4">
        <div className="relative">
          <textarea
            rows={1}
            className={`w-full resize-none rounded-lg border ${
              darkMode 
                ? 'border-gray-700 bg-gray-700 text-white focus:border-purple-500' 
                : 'border-gray-200 bg-white text-gray-900 focus:border-purple-500'
            } px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:opacity-50`}
            placeholder="Send a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
          />
          <button
            className={`absolute right-2 top-2.5 p-1 rounded-lg ${
              darkMode
                ? 'hover:bg-gray-600 text-purple-400'
                : 'hover:bg-purple-50 text-purple-500'
            } disabled:opacity-50`}
            onClick={handleSubmit}
            disabled={disabled || !input.trim()}
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        <p className={`mt-2 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          PharmAlchemy combines drug data analysis with AI to provide comprehensive answers.
        </p>
      </div>
    </div>
  );
}