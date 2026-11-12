import { useState, useEffect, useRef } from "react";
import { chatAPI } from "../utils/api";
import { useSettings } from "../contexts/SettingsContext";
import { useTranslation } from "../locales/translations";
import { Mic, MicOff, Volume2, VolumeX } from "lucide-react";

export default function VoiceAssistant({ commodity, mandi }) {
  const { language } = useSettings();
  const { t } = useTranslation(language);

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize Speech Recognition if available
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-IN';

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, [language]);

  // Toggle Voice Input (Mic)
  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Voice input is not supported in this browser. Please use Chrome or Edge.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // Text-to-Speech (Speak response aloud)
  const speakText = (text, index) => {
    if (!('speechSynthesis' in window)) return;

    if (speakingIndex === index) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*#•🌾💡📊🌦️⚠️🛡️📋]/g, '').trim();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
    utterance.onend = () => setSpeakingIndex(null);
    utterance.onerror = () => setSpeakingIndex(null);

    setSpeakingIndex(index);
    window.speechSynthesis.speak(utterance);
  };

  // Generate greeting message
  const makeGreeting = (c, m) => {
    if (language === 'hi') {
      return {
        role: "assistant",
        text: `🌾 **नमस्ते! मैं किसानमित्र AI हूँ।**\n\nमैं ${m || 'नासिक'} में ${c || 'प्याज'} के ताजा भाव, तेजी-मंदी और बिक्री सलाह देने के लिए उपलब्ध हूँ। मुझसे कोई भी सवाल पूछें!`,
      };
    }
    if (language === 'mr') {
      return {
        role: "assistant",
        text: `🌾 **नमस्कार! मी किसानमित्र AI आहे।**\n\nमी ${m || 'नाशिक'} मधील ${c || 'कांदा'} थेट दर आणि खरेदी-विक्रीचा सल्ला देण्यासाठी तयार आहे. मला काहीही विचारा!`,
      };
    }
    return {
      role: "assistant",
      text: `🌾 **Namaste! I am KisanMitra AI**, your intelligent agricultural advisor.\n\nAsk me direct questions like *"Can I buy ${c || 'Onion'} in ${m || 'Nashik'} after 7 days?"* or *"Should I sell now?"*`,
    };
  };

  // Set greeting on open or language/commodity/mandi change
  useEffect(() => {
    if (isOpen) {
      setMessages([makeGreeting(commodity, mandi)]);
    }
  }, [isOpen, commodity, mandi, language]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg = { role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const data = await chatAPI.sendMessage(trimmed, commodity || "", mandi || "", language);
      const assistantMsg = { role: "assistant", text: data.answer || "No response received." };
      setMessages((prev) => [...prev, assistantMsg]);
      
      // Auto-read aloud AI response for farmers
      speakText(assistantMsg.text, messages.length + 1);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: language === 'hi' ? "⚠️ सर्वर से संपर्क नहीं हो सका। कृपया पुनः प्रयास करें।" : "⚠️ Cannot connect to the server. Please try again later." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Floating button when closed
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-green-600 hover:bg-green-700 
                   text-white rounded-full shadow-lg hover:shadow-xl 
                   flex items-center justify-center transition-all duration-200
                   z-50 active:scale-95"
        title={t('chat_header')}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </button>
    );
  }

  // Chat panel when open
  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col bg-white rounded-2xl shadow-2xl border border-green-200 overflow-hidden"
      style={{ width: 360, height: 500 }}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-green-700 text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="min-w-0">
          <p className="font-bold text-sm truncate">🌾 {t('chat_header')}</p>
          <p className="text-green-100 text-xs truncate">
            {commodity && mandi
              ? `${commodity} • ${mandi}`
              : t('chat_subtitle')}
          </p>
        </div>
        <button
          onClick={() => {
            window.speechSynthesis?.cancel();
            setIsOpen(false);
          }}
          className="ml-2 w-7 h-7 rounded-full bg-green-500/30 hover:bg-green-500/50 
                     flex items-center justify-center transition-colors flex-shrink-0"
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-green-50/30">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[88%] px-3 py-2 rounded-xl text-sm leading-relaxed whitespace-pre-wrap relative ${
                msg.role === "user"
                  ? "bg-green-600 text-white rounded-br-sm"
                  : "bg-white border border-green-100 text-gray-800 rounded-bl-sm shadow-sm pr-8"
              }`}
            >
              {msg.text}
              {msg.role === "assistant" && (
                <button
                  onClick={() => speakText(msg.text, i)}
                  className="absolute top-2 right-2 p-1 text-gray-400 hover:text-green-600 transition-colors"
                  title="Read aloud"
                >
                  {speakingIndex === i ? <VolumeX className="w-4 h-4 text-green-600 animate-pulse" /> : <Volume2 className="w-4 h-4" />}
                </button>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-green-100 px-4 py-2 rounded-xl text-sm text-gray-500 shadow-sm flex items-center space-x-2">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input & Voice Controls */}
      <div className="border-t border-green-100 p-3 bg-white flex items-center space-x-2 flex-shrink-0">
        <button
          onClick={toggleListening}
          className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
            isListening ? "bg-red-500 text-white animate-pulse" : "bg-green-100 text-green-700 hover:bg-green-200"
          }`}
          title={isListening ? "Listening..." : "Click to Speak"}
        >
          {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? t('listening') : t('ask_placeholder')}
          className="flex-1 px-3 py-2 border border-green-200 rounded-lg text-sm 
                     focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-green-400"
          disabled={loading}
        />

        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm 
                     font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
        >
          {t('send_button')}
        </button>
      </div>
    </div>
  );
}
