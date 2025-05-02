import React from 'react';
import { motion } from 'framer-motion';
import { Brain, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Thought } from '../types';

interface ThoughtProcessProps {
  thoughts: Thought[];
  darkMode?: boolean;
}

export function ThoughtProcess({ thoughts, darkMode = false }: ThoughtProcessProps) {
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

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Brain className={`w-5 h-5 ${darkMode ? 'text-purple-400' : 'text-purple-600'}`} />
        <h3 className={`text-sm font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
          Reasoning Process
        </h3>
      </div>
      <div className="space-y-3">
        {thoughts.map((thought, index) => (
          <motion.div
            key={thought.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`flex items-start gap-3 p-4 rounded-lg ${
              darkMode 
                ? 'bg-gray-800/80 text-gray-200' 
                : 'bg-white/80 text-gray-700'
            } shadow-sm`}
          >
            <div className="flex-shrink-0 mt-1">
              {getStatusIcon(thought.status)}
            </div>
            <div className="flex-1">
              <div className="text-sm whitespace-pre-wrap leading-relaxed">
                {thought.content}
              </div>
              {thought.children && thought.children.length > 0 && (
                <div className="mt-3 pl-4 border-l-2 border-purple-200 dark:border-purple-800 space-y-3">
                  {thought.children.map((childThought, childIndex) => (
                    <motion.div
                      key={childThought.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: (index + childIndex + 1) * 0.1 }}
                      className="text-sm text-gray-600 dark:text-gray-400"
                    >
                      {childThought.content}
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}