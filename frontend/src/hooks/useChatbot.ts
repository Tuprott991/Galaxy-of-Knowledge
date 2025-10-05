import { useState, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  agent?: string;
  timestamp: number;
}

interface SessionInfo {
  userId: string;
  sessionId: string;
  appName: string;
}

interface TimelineEvent {
  type: string;
  data: unknown;
  timestamp: number;
}

export const useChatbot = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentSession, setCurrentSession] = useState<SessionInfo | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [websiteCount, setWebsiteCount] = useState(0);
  
  // Refs for streaming state
  const accumulatedTextRef = useRef("");
  const currentAgentRef = useRef<string>("");
  const abortControllerRef = useRef<AbortController | null>(null);

  const createSession = async (): Promise<SessionInfo> => {
    const generatedSessionId = uuidv4();
    
    const response = await fetch(`/apps/adk-agent/users/u_999/sessions/${generatedSessionId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ key: "value" })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    const sessionInfo = {
      userId: data.userId,
      sessionId: data.id,
      appName: data.appName
    };
    
    setCurrentSession(sessionInfo);
    return sessionInfo;
  };

  const retryWithBackoff = async (
    fn: () => Promise<Response>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<Response> => {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        if (attempt === maxRetries - 1) throw error;
        
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    throw new Error('Max retries exceeded');
  };

  const processSseEventData = (eventData: string, aiMessageId: string) => {
    try {
      const jsonData = JSON.parse(eventData);
      
      // Handle different event types
      if (jsonData.type === 'text_delta') {
        accumulatedTextRef.current += jsonData.content || '';
        currentAgentRef.current = jsonData.agent || currentAgentRef.current;
        
        // Update message incrementally
        setMessages(prev => prev.map(msg =>
          msg.id === aiMessageId
            ? { 
                ...msg, 
                content: accumulatedTextRef.current.trim(), 
                agent: currentAgentRef.current || msg.agent 
              }
            : msg
        ));
      } else if (jsonData.type === 'timeline_event') {
        setTimelineEvents(prev => [...prev, {
          type: jsonData.eventType,
          data: jsonData.data,
          timestamp: Date.now()
        }]);
      } else if (jsonData.type === 'website_count') {
        setWebsiteCount(jsonData.count);
      } else if (jsonData.type === 'agent_change') {
        currentAgentRef.current = jsonData.agent;
      }
    } catch (error) {
      console.warn('Failed to parse SSE event data:', error);
    }
  };

  const sendMessage = async (content: string, paperId?: string) => {
    if (!currentSession) {
      await createSession();
    }
    
    if (!currentSession) {
      throw new Error('Failed to create session');
    }

    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      content,
      role: 'user',
      timestamp: Date.now()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Reset streaming refs
    accumulatedTextRef.current = "";
    currentAgentRef.current = "";

    // Create AI message placeholder
    const aiMessageId = uuidv4();
    const aiMessage: Message = {
      id: aiMessageId,
      content: '',
      role: 'assistant',
      timestamp: Date.now()
    };
    
    setMessages(prev => [...prev, aiMessage]);

    // Abort previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();

    try {
      const sendMessageRequest = async () => {
        const requestBody = {
          prompt: content,
          ...(paperId && { paperId })
        };

        return await fetch(`/apps/adk-agent/users/${currentSession.userId}/sessions/${currentSession.sessionId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
          },
          body: JSON.stringify(requestBody),
          signal: abortControllerRef.current?.signal
        });
      };

      const response = await retryWithBackoff(sendMessageRequest);
      
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let lineBuffer = "";
      let eventDataBuffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          lineBuffer += decoder.decode(value, { stream: true });
          const lines = lineBuffer.split('\n');
          lineBuffer = lines.pop() || ""; // Keep incomplete line in buffer
          
          for (const line of lines) {
            if (line.startsWith('data:')) {
              eventDataBuffer += line.substring(5).trimStart() + '\n';
            } else if (line.trim() === "") {
              // Blank line indicates end of SSE event
              if (eventDataBuffer.trim()) {
                processSseEventData(eventDataBuffer.trim(), aiMessageId);
                eventDataBuffer = "";
              }
            }
          }
        }
        
        // Process any remaining data
        if (eventDataBuffer.trim()) {
          processSseEventData(eventDataBuffer.trim(), aiMessageId);
        }
        
      } finally {
        reader.releaseLock();
      }
      
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Request was aborted');
        return;
      }
      
      console.error('Error sending message:', error);
      
      // Update AI message with error
      setMessages(prev => prev.map(msg =>
        msg.id === aiMessageId
          ? { ...msg, content: 'Sorry, I encountered an error. Please try again.' }
          : msg
      ));
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const clearChat = () => {
    setMessages([]);
    setTimelineEvents([]);
    setWebsiteCount(0);
    accumulatedTextRef.current = "";
    currentAgentRef.current = "";
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const createNewSession = async () => {
    clearChat();
    await createSession();
  };

  return {
    messages,
    isLoading,
    currentSession,
    timelineEvents,
    websiteCount,
    sendMessage,
    createSession,
    createNewSession,
    clearChat
  };
};