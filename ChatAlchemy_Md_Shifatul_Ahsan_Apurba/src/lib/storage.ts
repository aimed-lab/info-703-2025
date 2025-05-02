import { Chat } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { openai } from './openai';

const STORAGE_KEY = 'chat_alchemy_chats';
const MAX_CHATS = 50; // Maximum number of chats to store
const MAX_MESSAGES_PER_CHAT = 100; // Maximum number of messages per chat

function cleanupChat(chat: Chat): Chat {
  return {
    ...chat,
    messages: chat.messages
      .slice(-MAX_MESSAGES_PER_CHAT) // Keep only the most recent messages
      .map(msg => ({
        ...msg,
        // Remove large data from older messages
        tableData: msg.tableData && chat.messages.indexOf(msg) < chat.messages.length - 1 
          ? undefined 
          : msg.tableData,
        thoughts: msg.thoughts && chat.messages.indexOf(msg) < chat.messages.length - 1
          ? undefined
          : msg.thoughts
      }))
  };
}

export async function generateChatName(content: string): Promise<string> {
  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "system",
          content: "You are a chat title generator. Generate a very short title (2-4 words only) based on the user's message. Focus on the main topic or medical term. Do not use punctuation. Example: 'Drug Interactions' or 'Cancer Treatment Research'"
        },
        {
          role: "user",
          content: `Generate a 2-4 word title for this chat: ${content}`
        }
      ],
      temperature: 0.7,
      max_tokens: 20
    });

    return completion.choices[0]?.message?.content?.trim() || 'New Chat';
  } catch (error) {
    console.error('Error generating chat name:', error);
    return 'New Chat';
  }
}

export function saveChat(chat: Chat): void {
  try {
    const chats = getAllChats();
    const existingIndex = chats.findIndex(c => c.id === chat.id);
    const cleanedChat = cleanupChat(chat);
    
    if (existingIndex >= 0) {
      chats[existingIndex] = {
        ...cleanedChat,
        updatedAt: new Date()
      };
    } else {
      // Remove oldest chats if we exceed the maximum
      while (chats.length >= MAX_CHATS) {
        const oldestChat = chats.reduce((oldest, current) => 
          current.updatedAt < oldest.updatedAt ? current : oldest
        );
        const index = chats.findIndex(c => c.id === oldestChat.id);
        if (index > -1) {
          chats.splice(index, 1);
        }
      }
      chats.push(cleanedChat);
    }
    
    // Sort by most recently updated
    chats.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
    } catch (storageError) {
      console.warn('Storage quota exceeded, cleaning up older data');
      
      // If storage fails, try removing more data
      const reducedChats = chats.map(c => ({
        id: c.id,
        name: c.name,
        messages: c.messages.slice(-20).map(msg => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp
        })),
        createdAt: c.createdAt,
        updatedAt: c.updatedAt
      }));
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(reducedChats));
    }
  } catch (error) {
    console.error('Error saving chat:', error);
  }
}

export function getAllChats(): Chat[] {
  try {
    const storedChats = localStorage.getItem(STORAGE_KEY);
    if (!storedChats) return [];
    
    const parsedChats = JSON.parse(storedChats);
    return parsedChats.map((chat: any) => ({
      ...chat,
      messages: chat.messages.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      })),
      createdAt: new Date(chat.createdAt),
      updatedAt: new Date(chat.updatedAt)
    }));
  } catch (error) {
    console.error('Error parsing chats from storage:', error);
    return [];
  }
}

export function getChatById(id: string): Chat | undefined {
  return getAllChats().find(chat => chat.id === id);
}

export function deleteChat(id: string): void {
  try {
    const chats = getAllChats().filter(chat => chat.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch (error) {
    console.error('Error deleting chat:', error);
  }
}

export function createNewChat(name: string = 'New Chat'): Chat {
  const newChat: Chat = {
    id: uuidv4(),
    name,
    messages: [],
    createdAt: new Date(),
    updatedAt: new Date()
  };
  
  saveChat(newChat);
  return newChat;
}

export function renameChat(id: string, newName: string): void {
  try {
    const chats = getAllChats();
    const chatIndex = chats.findIndex(chat => chat.id === id);
    
    if (chatIndex >= 0) {
      chats[chatIndex].name = newName;
      chats[chatIndex].updatedAt = new Date();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
    }
  } catch (error) {
    console.error('Error renaming chat:', error);
  }
}