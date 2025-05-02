import React from 'react';
import { User, FlaskRound as Flask } from 'lucide-react';
import { Message } from '../types';
import ReactMarkdown from 'react-markdown';

interface ChatMessageProps {
  message: Message;
  darkMode?: boolean;
}

export function ChatMessage({ message, darkMode = false }: ChatMessageProps) {
  const isUser = message.role === 'user';

  const handleQuestionClick = (question: string) => {
    // Remove the [Q1], [Q2], etc. prefix
    const cleanQuestion = question.replace(/^\[Q\d+\]\s*/, '').trim();
    
    // Create a new input event
    const event = new CustomEvent('question-click', {
      detail: { question: cleanQuestion }
    });
    window.dispatchEvent(event);
  };

  // Format the content by preserving line breaks and markdown formatting
  const formatContent = (content: string) => {
    return content
      // Normalize line endings
      .replace(/\r\n/g, '\n')
      // Preserve markdown line breaks
      .replace(/([^\n])\n([^\n])/g, '$1\n\n$2')
      // Handle bullet points
      .replace(/^[•-]\s*/gm, '* ')
      // Ensure proper spacing around headings
      .replace(/^(#{1,6})\s*/gm, '\n$1 ')
      // Clean up multiple blank lines
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  };

  // Check if the message contains clickable questions
  const hasClickableQuestions = message.content.includes('[Q');

  return (
    <div className={`py-6 ${
      isUser 
        ? darkMode ? 'bg-gray-800/50' : 'bg-white/50' 
        : darkMode ? 'bg-gray-800/80' : 'bg-white/80'
    }`}>
      <div className="max-w-[95%] mx-auto flex gap-4">
        <div className={`w-8 h-8 flex-shrink-0 mt-1 ${
          isUser 
            ? 'bg-gray-200 dark:bg-gray-700' 
            : 'bg-purple-100 dark:bg-purple-900'
        } rounded-full flex items-center justify-center`}>
          {isUser ? (
            <User className={`w-5 h-5 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`} />
          ) : (
            <Flask className={`w-5 h-5 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {isUser ? 'You' : 'PharmAlchemy'}
          </p>
          <div className="space-y-4">
            {hasClickableQuestions ? (
              <div className="space-y-2">
                {message.content.split('\n').map((line, index) => {
                  const questionMatch = line.match(/^\[Q\d+\]/);
                  if (questionMatch) {
                    return (
                      <button
                        key={index}
                        onClick={() => handleQuestionClick(line)}
                        className={`w-full text-left p-2 rounded text-base ${
                          darkMode 
                            ? 'hover:bg-purple-900/20 text-purple-300' 
                            : 'hover:bg-purple-50 text-purple-700'
                        } transition-colors whitespace-normal break-words`}
                      >
                        {line}
                      </button>
                    );
                  }
                  return (
                    <ReactMarkdown
                      key={index}
                      className={`prose ${darkMode ? 'dark:prose-invert' : ''} max-w-none`}
                      components={{
                        p: ({ children }) => (
                          <p className={`text-base leading-relaxed whitespace-pre-line break-words ${
                            darkMode ? 'text-gray-200' : 'text-gray-800'
                          }`}>
                            {children}
                          </p>
                        ),
                        strong: ({ children }) => (
                          <strong className={`font-bold ${darkMode ? 'text-purple-300' : 'text-purple-700'}`}>
                            {children}
                          </strong>
                        ),
                        em: ({ children }) => (
                          <em className="italic">
                            {children}
                          </em>
                        ),
                        blockquote: ({ children }) => (
                          <blockquote className={`border-l-4 pl-4 my-4 ${
                            darkMode 
                              ? 'border-purple-500 bg-purple-900/10' 
                              : 'border-purple-300 bg-purple-50'
                          } py-2 rounded-r`}>
                            {children}
                          </blockquote>
                        ),
                        code: ({ children }) => (
                          <code className={`px-1.5 py-0.5 rounded ${
                            darkMode 
                              ? 'bg-gray-700 text-purple-300' 
                              : 'bg-gray-100 text-purple-700'
                          }`}>
                            {children}
                          </code>
                        ),
                        h1: ({ children }) => (
                          <h1 className={`text-2xl font-bold mt-6 mb-4 ${
                            darkMode ? 'text-gray-100' : 'text-gray-900'
                          }`}>
                            {children}
                          </h1>
                        ),
                        h2: ({ children }) => (
                          <h2 className={`text-xl font-bold mt-5 mb-3 ${
                            darkMode ? 'text-gray-200' : 'text-gray-800'
                          }`}>
                            {children}
                          </h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className={`text-lg font-bold mt-4 mb-2 ${
                            darkMode ? 'text-gray-300' : 'text-gray-700'
                          }`}>
                            {children}
                          </h3>
                        ),
                        ul: ({ children }) => (
                          <ul className="space-y-2 my-4 list-disc pl-6">
                            {children}
                          </ul>
                        ),
                        ol: ({ children }) => (
                          <ol className="space-y-2 my-4 list-decimal pl-6">
                            {children}
                          </ol>
                        ),
                        li: ({ children }) => (
                          <li className={`text-base leading-relaxed ${
                            darkMode ? 'text-gray-200' : 'text-gray-800'
                          }`}>
                            {children}
                          </li>
                        ),
                        hr: () => (
                          <hr className={`my-6 border-t ${
                            darkMode ? 'border-gray-700' : 'border-gray-200'
                          }`} />
                        )
                      }}
                    >
                      {line}
                    </ReactMarkdown>
                  );
                })}
              </div>
            ) : (
              <ReactMarkdown
                className={`prose ${darkMode ? 'dark:prose-invert' : ''} max-w-none`}
                components={{
                  p: ({ children }) => (
                    <p className={`text-base leading-relaxed whitespace-pre-line break-words ${
                      darkMode ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      {children}
                    </p>
                  ),
                  strong: ({ children }) => (
                    <strong className={`font-bold ${darkMode ? 'text-purple-300' : 'text-purple-700'}`}>
                      {children}
                    </strong>
                  ),
                  em: ({ children }) => (
                    <em className="italic">
                      {children}
                    </em>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className={`border-l-4 pl-4 my-4 ${
                      darkMode 
                        ? 'border-purple-500 bg-purple-900/10' 
                        : 'border-purple-300 bg-purple-50'
                    } py-2 rounded-r`}>
                      {children}
                    </blockquote>
                  ),
                  code: ({ children }) => (
                    <code className={`px-1.5 py-0.5 rounded ${
                      darkMode 
                        ? 'bg-gray-700 text-purple-300' 
                        : 'bg-gray-100 text-purple-700'
                    }`}>
                      {children}
                    </code>
                  ),
                  h1: ({ children }) => (
                    <h1 className={`text-2xl font-bold mt-6 mb-4 ${
                      darkMode ? 'text-gray-100' : 'text-gray-900'
                    }`}>
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className={`text-xl font-bold mt-5 mb-3 ${
                      darkMode ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className={`text-lg font-bold mt-4 mb-2 ${
                      darkMode ? 'text-gray-300' : 'text-gray-700'
                    }`}>
                      {children}
                    </h3>
                  ),
                  ul: ({ children }) => (
                    <ul className="space-y-2 my-4 list-disc pl-6">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="space-y-2 my-4 list-decimal pl-6">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className={`text-base leading-relaxed ${
                      darkMode ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      {children}
                    </li>
                  ),
                  hr: () => (
                    <hr className={`my-6 border-t ${
                      darkMode ? 'border-gray-700' : 'border-gray-200'
                    }`} />
                  )
                }}
              >
                {formatContent(message.content)}
              </ReactMarkdown>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}