import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Thought } from '../types';
import { Brain, CheckCircle, XCircle, Clock } from 'lucide-react';

interface ThoughtTreeProps {
  thoughts: Thought[];
  darkMode?: boolean;
}

export function ThoughtTree({ thoughts, darkMode = false }: ThoughtTreeProps) {
  const getStatusIcon = (status: Thought['status']) => {
    switch (status) {
      case 'thinking':
        return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const renderThought = (thought: Thought, level: number = 0) => {
    return (
      <motion.div
        key={thought.id}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 20 }}
        transition={{ duration: 0.3, delay: level * 0.1 }}
        className={`mt-3 first:mt-0 ${level > 0 ? 'ml-6' : ''}`}
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            {getStatusIcon(thought.status)}
          </div>
          <div className={`flex-1 p-3 rounded-lg ${
            darkMode 
              ? 'bg-gray-800 text-gray-200' 
              : 'bg-white text-gray-700'
          } shadow-sm`}>
            <div className="text-sm whitespace-pre-wrap">{thought.content}</div>
          </div>
        </div>
        {thought.children && thought.children.length > 0 && (
          <div className="mt-2 space-y-2 border-l-2 border-dashed pl-6 ml-2 border-gray-300 dark:border-gray-600">
            {thought.children.map(child => renderThought(child, level + 1))}
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Brain className={`w-5 h-5 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
        <h3 className={`text-sm font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
          Reasoning Process
        </h3>
      </div>
      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {thoughts.map(thought => renderThought(thought))}
        </AnimatePresence>
      </div>
    </div>
  );
}