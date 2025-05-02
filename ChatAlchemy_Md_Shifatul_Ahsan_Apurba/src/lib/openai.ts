import OpenAI from 'openai';

export const openai = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true
});

export const assistantId = import.meta.env.VITE_OPENAI_ASSISTANT_ID;

export async function getAssistantResponse(messages: { role: string; content: string }[]) {
  try {
    // Create a thread
    const thread = await openai.beta.threads.create();

    // Add messages to the thread
    for (const message of messages) {
      if (message.role === 'user') {
        await openai.beta.threads.messages.create(thread.id, {
          role: 'user',
          content: message.content
        });
      }
    }

    // Run the assistant
    const run = await openai.beta.threads.runs.create(thread.id, {
      assistant_id: assistantId,
      instructions: `Assume the role of PharmaAlchemy, a knowledgeable assistant capable of drug discovery, molecule analysis, and finding molecules using data.

CORE REQUIREMENTS:
1. Begin EVERY response with "According to PharmaAlchemy"
2. Be concise unless the user requests a "Detailed answer"
3. Use proper markdown formatting:
   - Use **bold** for important terms and drug names
   - Use bullet points for lists
   - Use numbered lists for steps or sequences
   - Use > for important quotes or highlights
   - Use proper headings with # for sections
   - Use --- for section breaks when needed
   - Use \`code\` for chemical formulas or technical terms
4. ALWAYS cite sources using the format【number:1†source】within the text
5. If data is unavailable in primary sources, use internet resources or existing knowledge
6. For table requests, provide answers in CSV-ready format
7. Present information directly and confidently as your own knowledge
8. Keep responses focused on pharmaceutical and medical information
9. Use a professional yet approachable tone that reflects expertise in pharmaceuticals

FORMATTING GUIDELINES:
1. Structure responses with clear sections using markdown headings
2. Use bullet points for listing multiple items
3. Use numbered lists for sequential steps
4. Highlight key terms with **bold**
5. Use blockquotes (>) for important notes or warnings
6. Maintain consistent spacing between sections
7. Use horizontal rules (---) to separate major sections
8. Format chemical formulas and technical terms with \`backticks\`

RESPONSE STRUCTURE:
1. Start with "According to PharmaAlchemy"
2. Present main content with inline source citations【number:1†source】
3. Use appropriate markdown formatting throughout
4. If applicable, include CSV-formatted data for tables
5. End with a "Sources:" section listing all referenced sources

Remember to maintain a professional, medical-focused tone while ensuring information is clear and accessible.`
    });

    // Poll for completion
    let runStatus = await openai.beta.threads.runs.retrieve(thread.id, run.id);
    let attempts = 0;
    const maxAttempts = 30; // 30 seconds timeout

    while (runStatus.status !== 'completed' && attempts < maxAttempts) {
      if (runStatus.status === 'failed' || runStatus.status === 'cancelled') {
        throw new Error(`Run ${runStatus.status}: ${runStatus.last_error?.message || 'Unknown error'}`);
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
      runStatus = await openai.beta.threads.runs.retrieve(thread.id, run.id);
      attempts++;
    }

    if (attempts >= maxAttempts) {
      throw new Error('Request timed out after 30 seconds');
    }

    // Get the messages
    const messages_response = await openai.beta.threads.messages.list(thread.id);
    const lastMessage = messages_response.data[0];

    if (!lastMessage || !lastMessage.content[0]?.text?.value) {
      throw new Error('No response received from assistant');
    }

    // Clean up the thread
    await openai.beta.threads.del(thread.id).catch(console.error);

    return {
      content: lastMessage.content[0].text.value,
      role: 'assistant'
    };
  } catch (error: any) {
    console.error('Error getting assistant response:', error);
    return {
      content: `I apologize, but I encountered an error: ${error.message || 'Unknown error'}. Please try again.`,
      role: 'assistant'
    };
  }
}