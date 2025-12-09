import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Alert, AlertDescription } from './ui/alert';
import { Mic, MicOff, Volume2, Send, User, Bot, AlertTriangle, Sparkles } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown'; // <-- 1. IMPORT THE NEW PACKAGE

// REMOVED THE BACKEND_URL AND API CONSTANTS
// The proxy in package.json will handle requests to /api/*

const Chat = () => {
  const navigate = useNavigate();
  const [language, setLanguage] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const savedLanguage = localStorage.getItem('selected_language');
    if (!savedLanguage) {
      navigate('/');
      return;
    }
    setLanguage(savedLanguage);
    fetchAlerts();
    loadWelcomeMessage(savedLanguage);
  }, [navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const welcomeMessages = {
    en: 'Hello! I am Aacharya, your health assistant. Ask me anything about health, diseases, symptoms, or available medical supplies.',
    hi: 'नमस्ते! मैं आचार्य हूँ, आपका स्वास्थ्य सहायक। मुझसे स्वास्थ्य, बीमारियों, लक्षणों या उपलब्ध चिकित्सा सामग्री के बारे में कुछ भी पूछें।',
    kn: 'ನಮಸ್ಕಾರ! ನಾನು ಆಚಾರ್ಯ, ನಿಮ್ಮ ಆರೋಗ್ಯ ಸಹಾಯಕ. ಆರೋಗ್ಯ, ರೋಗಗಳು, ಲಕ್ಷಣಗಳು ಅಥವಾ ಲಭ್ಯವಿರುವ ಔಷಧ ಸಾಮಗ್ರಿಗಳ ಬಗ್ಗೆ ನನ್ನ ಯಾವುದರಲ್ಲಿ ಕೇಳಿ.'
  };

  const loadWelcomeMessage = (lang) => {
    setMessages([{
      type: 'bot',
      text: welcomeMessages[lang] || welcomeMessages.en
    }]);
  };

  const fetchAlerts = async () => {
    try {
      // UPDATED URL: Changed to relative path
      const response = await axios.get('/api/get-alerts');
      setAlerts(response.data);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = inputText;
    setInputText('');
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      // UPDATED URL: Changed to relative path
      const response = await axios.post('/api/chat', {
        query: userMessage,
        language: language
      });

      setMessages(prev => [...prev, { type: 'bot', text: response.data.response }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { 
        type: 'bot', 
        text: language === 'hi' ? 'क्षमा करें, कोई त्रुटि हुई।' : 
              language === 'kn' ? 'ಕ್ಷಮಿಸಿ, ತಪ್ಪು ಆಗಿದೆ.' : 
              'Sorry, an error occurred.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const startListening = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in your browser.');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    const languageCodes = {
      en: 'en-US',
      hi: 'hi-IN',
      kn: 'kn-IN'
    };
    
    recognition.lang = languageCodes[language] || 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInputText(transcript);
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
    recognitionRef.current = recognition;
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      // --- THIS IS THE FIX ---
      // Stop any speech that is currently playing
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      const languageCodes = {
        en: 'en-US',
        hi: 'hi-IN',
        kn: 'kn-IN'
      };
      utterance.lang = languageCodes[language] || 'en-US';
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    // Make the main container a full-height flex column
    <div className="flex flex-col h-screen bg-bg-light" style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div className="bg-gradient-to-r from-deep-blue to-blue-700 text-white p-4 shadow-xl">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="bg-white/10 p-2 rounded-lg backdrop-blur-sm">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" data-testid="chat-header">
                Aacharya AI
              </h1>
              <p className="text-xs text-blue-100">Your Health Companion</p>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={() => navigate('/login')}
            data-testid="worker-login-link"
            className="bg-white/10 text-white hover:bg-white/20 border-white/30 backdrop-blur-sm"
          >
            Health Worker Login
          </Button>
        </div>
      </div>

      {/* Alerts - Carousel Style */}
      {alerts.length > 0 && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-amber-400 py-3" data-testid="alerts-container">
          <div className="container mx-auto overflow-x-auto">
            <div className="flex space-x-4 px-4">
              {alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="flex-shrink-0 min-w-[300px] bg-white rounded-xl p-3 shadow-sm border border-amber-200">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-amber-900 font-medium">{alert.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* This container now grows to fill space and scrolls */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 container mx-auto" data-testid="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            data-testid={`message-${message.type}-${index}`}
          >
            <div className={`flex items-start max-w-[75%] md:max-w-[65%] ${
              message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}>
              <div className={`flex-shrink-0 ${
                message.type === 'user' ? 'ml-2' : 'mr-2'
              }`}>
                {message.type === 'user' ? (
                  <div className="bg-gradient-to-br from-electric-teal to-teal-600 p-2 rounded-full shadow-md">
                    <User className="w-4 h-4 text-white" />
                  </div>
                ) : (
                  <div className="bg-gradient-to-br from-deep-blue to-blue-600 p-2 rounded-full shadow-md">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
              <div>
                {message.type === 'bot' && (
                  <p className="text-xs text-gray-500 mb-1 ml-1 font-medium">Aacharya</p>
                )}
                <div className={`p-4 shadow-sm ${
                  message.type === 'user' 
                    ? 'chat-bubble-user text-white' 
                    : 'chat-bubble-ai text-gray-800 border border-gray-200'
                }`}>
                  
                  {/* --- 2. REPLACE THE <p> TAG WITH THIS --- */}
                  <div className="text-sm md:text-base leading-relaxed">
                    <ReactMarkdown
                      components={{
                        // Style lists to look nice
                        ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-1" {...props} />,
                        // Style bold text
                        strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                      }}
                    >
                      {message.text}
                    </ReactMarkdown>
                  </div>
                  {/* --- END OF REPLACEMENT --- */}

                  {message.type === 'bot' && (
                    <button
                      onClick={() => speakText(message.text)}
                      className="mt-2 text-deep-blue hover:text-electric-teal transition-colors p-1 rounded-lg hover:bg-white/50"
                      data-testid={`speak-button-${index}`}
                      aria-label="Speak message"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-start">
              <div className="bg-gradient-to-br from-deep-blue to-blue-600 p-2 rounded-full shadow-md mr-2">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                {/* --- TYPO FIX HERE --- */}
                <p className="text-xs text-gray-500 mb-1 ml-1 font-medium">Aacharya</p>
                <div className="chat-bubble-ai border border-gray-200 p-4 shadow-sm">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-electric-teal rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-electric-teal rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-electric-teal rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* This is now a direct child of the flex container */}
      <div className="bg-white rounded-t-2xl shadow-xl p-3 border-t-2 border-gray-200">
        <div className="container mx-auto flex items-center space-x-2">
          <Button
            onClick={isListening ? stopListening : startListening}
            variant="outline"
            size="icon"
            data-testid="voice-input-button"
            className={`flex-shrink-0 w-12 h-12 rounded-xl ${
              isListening 
                ? 'bg-red-500 hover:bg-red-600 text-white border-red-500 animate-pulse' 
                : 'bg-gradient-to-br from-deep-blue to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border-deep-blue shadow-md'
            }`}
          >
            {isListening ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
          </Button>
          <Input
            type="text"
            placeholder={language === 'hi' ? 'अपना सवाल यहाँ टाइप करें...' : 
                         language === 'kn' ? 'ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಇಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ...' : 
                         'Type your question here...'}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            data-testid="chat-input"
            className="flex-1 border-gray-300 focus:border-electric-teal focus:ring-electric-teal rounded-xl h-12 text-base"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputText.trim() || isLoading}
            data-testid="send-message-button"
            className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-electric-teal to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white rounded-xl shadow-md"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Chat;

