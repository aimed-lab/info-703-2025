import React, { useState, useEffect } from 'react';
import { Message, Chat } from './types';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { ChatHeader } from './components/ChatHeader';
import { BiomedicalModule } from './components/biomedical/BiomedicalModule';
import { getAssistantResponse } from './lib/openai';
import { searchKnowledgeBase, clearData, getLoadedFiles, loadBackendData } from './lib/knowledge';
import { getAllChats, getChatById, saveChat, createNewChat, generateChatName, deleteChat } from './lib/storage';
import { v4 as uuidv4 } from 'uuid';
import { MessageSquare, Plus, Dna, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

function App() {
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadedFiles, setLoadedFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showBiomedical, setShowBiomedical] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme === 'dark' || 
      (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const count = await loadBackendData();
        if (count > 0) {
          setLoadedFiles(getLoadedFiles());
        }
      } catch (error) {
        console.error('Error loading backend data:', error);
        setError('Failed to load initial data. Please try refreshing the page.');
      }
    };
    loadData();
  }, []);

  const handleNewChat = () => {
    const newChat = createNewChat();
    
    const welcomeMessage: Message = {
      id: uuidv4(),
      role: 'assistant',
      content: "I am PharmAlchemy, your pharmaceutical data assistant. I specialize in drug and disease information from my knowledge base. How can I help you today?",
      timestamp: new Date(),
    };
    
    newChat.messages = [welcomeMessage];
    saveChat(newChat);
    
    setCurrentChat({...newChat});
    setShowBiomedical(false);
    setShowChat(true);
    setError(null);
  };

  const handleSelectChat = (chatId: string) => {
    const chat = getChatById(chatId);
    if (chat) {
      setCurrentChat({...chat});
      setShowBiomedical(false);
      setShowChat(true);
      setError(null);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    deleteChat(chatId);
    setCurrentChat(null);
    setShowChat(false);
    setShowBiomedical(false);
  };

  const handleFileUpload = (filename: string) => {
    setLoadedFiles(getLoadedFiles());
    
    if (currentChat) {
      const newMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: `Successfully loaded ${filename}. You can now ask questions about the data.`,
        timestamp: new Date(),
      };
      
      const updatedChat = {
        ...currentChat,
        messages: [...currentChat.messages, newMessage],
        updatedAt: new Date()
      };
      
      setCurrentChat(updatedChat);
      saveChat(updatedChat);
    }
    
    setError(null);
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleClearData = () => {
    clearData();
    setLoadedFiles([]);
    
    if (currentChat) {
      const newMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'All data has been cleared. Please upload new files to interact with your file or continue with PharmAlchemy.',
        timestamp: new Date(),
      };
      
      const updatedChat = {
        ...currentChat,
        messages: [...currentChat.messages, newMessage],
        updatedAt: new Date()
      };
      
      setCurrentChat(updatedChat);
      saveChat(updatedChat);
    }
  };

  const toggleTheme = () => {
    setDarkMode(!darkMode);
  };

  const handleTransferFromBiomedical = () => {
    // Get the most recently created chat
    const chats = getAllChats();
    const latestChat = chats[0]; // Chats are sorted by updatedAt
    if (latestChat) {
      setCurrentChat({...latestChat});
      setShowChat(true);
    }
  };

  const handleToggleSplitView = () => {
    setShowChat(!showChat);
  };

  const handleGoHome = () => {
    setCurrentChat(null);
    setShowBiomedical(false);
    setShowChat(false);
  };

  const handleSendMessage = async (content: string) => {
    if (!currentChat) return;
    
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    const updatedChat = {
      ...currentChat,
      messages: [...currentChat.messages, userMessage],
      updatedAt: new Date()
    };

    // Generate chat name if this is the first user message
    if (currentChat.messages.length === 1) { // Only welcome message
      const chatName = await generateChatName(content);
      updatedChat.name = chatName;
    }
    
    setCurrentChat(updatedChat);
    saveChat(updatedChat);
    
    setIsLoading(true);
    setError(null);

    try {
      const result = await searchKnowledgeBase(content);
      
      const contextMessages = updatedChat.messages.slice(-5).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      if (result.text) {
        contextMessages.push({
          role: 'user',
          content: `Context: ${result.text}`
        });
      }

      const response = await getAssistantResponse(contextMessages);

      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date()
      };
      
      const finalChat = {
        ...updatedChat,
        messages: [...updatedChat.messages, assistantMessage],
        updatedAt: new Date()
      };
      
      setCurrentChat(finalChat);
      saveChat(finalChat);
    } catch (error: any) {
      console.error('Error processing request:', error);
      setError('There was an error processing your request. Please try again.');
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date()
      };
      
      const errorChat = {
        ...updatedChat,
        messages: [...updatedChat.messages, errorMessage],
        updatedAt: new Date()
      };
      
      setCurrentChat(errorChat);
      saveChat(errorChat);
    } finally {
      setIsLoading(false);
    }
  };

  const renderChatInterface = () => (
    <div className="flex-1 flex flex-col overflow-hidden">
      {error && (
        <div className="max-w-[95%] mx-auto w-full mt-2 text-sm text-red-500 bg-red-50 dark:bg-red-900/20 p-2 rounded">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto bg-gradient-to-b from-purple-50 to-white dark:from-gray-900 dark:to-gray-800">
        <div className="max-w-[95%] mx-auto">
          {currentChat?.messages.map((message) => (
            <ChatMessage 
              key={message.id}
              message={message} 
              darkMode={darkMode}
            />
          ))}
          
          {isLoading && (
            <div className="py-4 px-4">
              <div className="flex gap-2 items-center text-sm text-gray-500 dark:text-gray-400">
                <div className="w-2 h-2 bg-purple-600 dark:bg-purple-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-600 dark:bg-purple-500 rounded-full animate-bounce [animation-delay:-.3s]" />
                <div className="w-2 h-2 bg-purple-600 dark:bg-purple-500 rounded-full animate-bounce [animation-delay:-.5s]" />
              </div>
            </div>
          )}
        </div>
      </div>

      <ChatInput onSend={handleSendMessage} disabled={isLoading} darkMode={darkMode} />
    </div>
  );

  const renderLandingPage = () => {
    const existingChats = getAllChats();

    return (
      <div className="h-[calc(100vh-4rem)] bg-gradient-to-b from-purple-50 to-white dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
        <div className="max-w-2xl w-full space-y-8">
          <div className="text-center">
            <h1 className={`text-4xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Welcome to ChatAlchemy
            </h1>
            <p className={`text-lg ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Your intelligent pharmaceutical data assistant for PharmAlchemy
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* New Chat Card */}
            <button
              onClick={handleNewChat}
              className={`p-6 rounded-xl border-2 text-left transition-all transform hover:scale-105 ${
                darkMode 
                  ? 'bg-gray-800 border-purple-500 hover:bg-gray-700' 
                  : 'bg-white border-purple-200 hover:border-purple-500'
              }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <Plus className={`h-6 w-6 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  ChatAlchemy
                </h2>
              </div>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Start a new conversation with ChatAlchemy
              </p>
            </button>

            {/* Biomedical Module Card */}
            <button
              onClick={() => {
                setShowBiomedical(true);
                setCurrentChat(null);
                setShowChat(false);
              }}
              className={`p-6 rounded-xl border-2 text-left transition-all transform hover:scale-105 ${
                darkMode 
                  ? 'bg-gray-800 border-purple-500 hover:bg-gray-700' 
                  : 'bg-white border-purple-200 hover:border-purple-500'
              }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <Dna className={`h-6 w-6 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                <h2 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  Biomedical Analysis
                </h2>
              </div>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Analyze biomedical data and research papers
              </p>
            </button>
          </div>

          {/* Recent Chats Section */}
          {existingChats.length > 0 && (
            <div className={`p-6 rounded-xl ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <h2 className={`text-xl font-semibold mb-4 flex items-center gap-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                <MessageSquare className={`h-5 w-5 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
                Recent Conversations
              </h2>
              <div className="max-h-[250px] overflow-y-auto">
                {existingChats.slice(0, 5).map(chat => (
                  <button
                    key={chat.id}
                    onClick={() => handleSelectChat(chat.id)}
                    className={`w-full p-3 rounded-lg text-left transition-colors ${
                      darkMode 
                        ? 'hover:bg-gray-700 text-gray-300' 
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{chat.name}</span>
                      <span className="text-sm text-gray-500">
                        {new Date(chat.updatedAt).toLocaleDateString()}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`flex flex-col h-screen ${darkMode ? 'dark' : ''}`}>
      <ChatHeader
        chatName={currentChat?.name || (showBiomedical ? 'Biomedical Analysis' : 'ChatAlchemy')}
        chatId={currentChat?.id || null}
        loadedFiles={loadedFiles}
        onClearData={handleClearData}
        onFileUpload={handleFileUpload}
        onUploadError={handleUploadError}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        darkMode={darkMode}
        toggleTheme={toggleTheme}
        onToggleBiomedical={() => {
          if (showBiomedical) {
            setShowBiomedical(false);
            setShowChat(true);
            if (!currentChat) {
              const chats = getAllChats();
              if (chats.length > 0) {
                setCurrentChat({...chats[0]});
              }
            }
          } else {
            setShowBiomedical(true);
            setCurrentChat(null);
            setShowChat(false);
          }
        }}
        showBiomedical={showBiomedical}
        onGoHome={handleGoHome}
      />

      {currentChat || showBiomedical ? (
        <div className="flex-1 flex overflow-hidden relative">
          {showBiomedical && (
            <div className={`${showChat ? 'w-1/2' : 'w-full'} overflow-y-auto`}>
              <BiomedicalModule onTransferToChat={handleTransferFromBiomedical} />
            </div>
          )}
          
          {currentChat && showChat && (
            <div className={`${showBiomedical ? 'w-1/2' : 'w-full'} flex flex-col overflow-hidden border-l border-gray-200 dark:border-gray-700`}>
              {renderChatInterface()}
            </div>
          )}

          {currentChat && showBiomedical && (
            <button
              onClick={handleToggleSplitView}
              className={`fixed p-2 rounded-full ${
                darkMode 
                  ? 'bg-gray-800 text-gray-300 hover:bg-gray-700' 
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              } shadow-lg ${showChat ? 'right-[calc(50%-1.5rem)]' : 'right-4'} top-20 z-30`}
              title={showChat ? "Close chat" : "Open chat"}
            >
              {showChat ? (
                <PanelLeftClose className="h-5 w-5" />
              ) : (
                <PanelLeftOpen className="h-5 w-5" />
              )}
            </button>
          )}
        </div>
      ) : (
        renderLandingPage()
      )}
    </div>
  );
}

export default App;