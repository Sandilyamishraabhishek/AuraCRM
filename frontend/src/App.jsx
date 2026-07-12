import React, { useEffect, useState, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setHcpsStart, setHcpsSuccess, setHcpsFailure,
  setMaterialsStart, setMaterialsSuccess, setMaterialsFailure,
  setInteractionsStart, setInteractionsSuccess, setInteractionsFailure,
  addInteraction, updateInteraction, removeInteraction,
  addMessage, setChatLoading, setExtractedForm, clearExtractedForm
} from './store'
import { 
  Users, 
  FileText, 
  Send, 
  Sparkles, 
  Activity, 
  CheckSquare, 
  Edit3, 
  Trash2,
  AlertCircle,
  FileSpreadsheet,
  RefreshCw,
  PlusCircle,
  Clock,
  ThumbsUp,
  Meh,
  ThumbsDown
} from 'lucide-react'

const API_BASE = "http://localhost:8000/api"

export default function App() {
  const dispatch = useDispatch()
  const hcps = useSelector(state => state.hcps.list)
  const materials = useSelector(state => state.materials.list)
  const interactions = useSelector(state => state.interactions.list)
  const chat = useSelector(state => state.chat)
  
  // Form State
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    hcp_id: "",
    interaction_type: "Meeting",
    date: new Date().toISOString().split('T')[0],
    time: new Date().toTimeString().split(' ')[0].slice(0, 5),
    attendees: "",
    topics_discussed: "",
    sentiment: "Neutral",
    outcomes: "",
    follow_up_actions: "",
    materials_shared: [],
    samples_distributed: []
  })
  
  // Chat input
  const [chatInput, setChatInput] = useState("")
  const chatEndRef = useRef(null)

  // Fetch initial data
  const fetchData = async () => {
    try {
      dispatch(setHcpsStart())
      const hcpRes = await fetch(`${API_BASE}/hcps`)
      const hcpData = await hcpRes.json()
      dispatch(setHcpsSuccess(hcpData))
      
      dispatch(setMaterialsStart())
      const matRes = await fetch(`${API_BASE}/materials`)
      const matData = await matRes.json()
      dispatch(setMaterialsSuccess(matData))
      
      dispatch(setInteractionsStart())
      const intRes = await fetch(`${API_BASE}/interactions`)
      const intData = await intRes.json()
      dispatch(setInteractionsSuccess(intData))
    } catch (err) {
      console.error(err)
      dispatch(setHcpsFailure(err.message))
      dispatch(setMaterialsFailure(err.message))
      dispatch(setInteractionsFailure(err.message))
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat.messages])

  // Handle Form Inputs
  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleCheckboxChange = (name, item, checked) => {
    setFormData(prev => {
      const list = prev[name] ? [...prev[name]] : []
      if (checked) {
        if (!list.includes(item)) list.push(item)
      } else {
        const idx = list.indexOf(item)
        if (idx !== -1) list.splice(idx, 1)
      }
      return { ...prev, [name]: list }
    })
  }

  // Submit Logged Interaction
  const handleFormSubmit = async (e) => {
    e.preventDefault()
    if (!formData.hcp_id) {
      alert("Please select a Healthcare Professional (HCP)")
      return
    }

    const payload = {
      ...formData,
      hcp_id: parseInt(formData.hcp_id),
      materials_shared: formData.materials_shared.join(", "),
      samples_distributed: formData.samples_distributed.join(", ")
    }

    try {
      if (editingId) {
        // Edit flow
        const res = await fetch(`${API_BASE}/interactions/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        if (res.ok) {
          const updated = await res.json()
          dispatch(updateInteraction(updated))
          alert("Interaction updated successfully!")
          resetForm()
          fetchData() // refresh stocks
        } else {
          alert("Failed to update interaction")
        }
      } else {
        // Log flow
        const res = await fetch(`${API_BASE}/interactions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        if (res.ok) {
          const logged = await res.json()
          dispatch(addInteraction(logged))
          alert("Interaction logged successfully!")
          resetForm()
          fetchData() // refresh stocks
        } else {
          alert("Failed to log interaction")
        }
      }
    } catch (err) {
      console.error(err)
      alert("Error logging interaction")
    }
  }

  // Edit action from list
  const startEdit = (item) => {
    setEditingId(item.id)
    setFormData({
      hcp_id: item.hcp_id.toString(),
      interaction_type: item.interaction_type,
      date: item.date,
      time: item.time,
      attendees: item.attendees || "",
      topics_discussed: item.topics_discussed || "",
      sentiment: item.sentiment || "Neutral",
      outcomes: item.outcomes || "",
      follow_up_actions: item.follow_up_actions || "",
      materials_shared: item.materials_shared ? item.materials_shared.split(", ").filter(Boolean) : [],
      samples_distributed: item.samples_distributed ? item.samples_distributed.split(", ").filter(Boolean) : []
    })
  }

  // Delete action
  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this interaction?")) return
    try {
      const res = await fetch(`${API_BASE}/interactions/${id}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        dispatch(removeInteraction(id))
        if (editingId === id) resetForm()
        alert("Interaction deleted.")
      }
    } catch (err) {
      console.error(err)
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setFormData({
      hcp_id: "",
      interaction_type: "Meeting",
      date: new Date().toISOString().split('T')[0],
      time: new Date().toTimeString().split(' ')[0].slice(0, 5),
      attendees: "",
      topics_discussed: "",
      sentiment: "Neutral",
      outcomes: "",
      follow_up_actions: "",
      materials_shared: [],
      samples_distributed: []
    })
  }

  // Send message to AI Assistant
  const handleSendMessage = async (msgText = chatInput) => {
    const textToSend = msgText || chatInput
    if (!textToSend.trim()) return

    dispatch(addMessage({ role: 'user', content: textToSend }))
    setChatInput("")
    dispatch(setChatLoading(true))

    try {
      const chatHistory = chat.messages.map(m => ({ role: m.role, content: m.content }))
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          history: chatHistory
        })
      })
      if (res.ok) {
        const data = await res.json()
        dispatch(addMessage({ role: 'assistant', content: data.reply }))
        if (data.form_data && Object.keys(data.form_data).length > 0) {
          dispatch(setExtractedForm(data.form_data))
        }
        fetchData() // Refresh list/stocks in case tool executed database operations
      } else {
        dispatch(addMessage({ role: 'assistant', content: "Sorry, I had trouble processing that request." }))
      }
    } catch (err) {
      console.error(err)
      dispatch(addMessage({ role: 'assistant', content: "Network error occurred while contacting AI Assistant." }))
    } finally {
      dispatch(setChatLoading(false))
    }
  }

  // Apply AI Extracted Form
  const applyAIExtractedForm = () => {
    const ext = chat.extractedForm
    setFormData(prev => ({
      ...prev,
      hcp_id: ext.hcp_id ? ext.hcp_id.toString() : prev.hcp_id,
      interaction_type: ext.interaction_type || prev.interaction_type,
      date: ext.date || prev.date,
      time: ext.time || prev.time,
      topics_discussed: ext.topics_discussed || prev.topics_discussed,
      sentiment: ext.sentiment || prev.sentiment,
      materials_shared: ext.materials_shared ? ext.materials_shared.split(", ").filter(Boolean) : prev.materials_shared,
      samples_distributed: ext.samples_distributed ? ext.samples_distributed.split(", ").filter(Boolean) : prev.samples_distributed,
      follow_up_actions: ext.follow_up_actions || prev.follow_up_actions
    }))
    dispatch(clearExtractedForm())
    alert("Form populated with AI extracted data!")
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header glass-panel">
        <div className="logo-section">
          <div className="logo-icon">🩺</div>
          <div className="logo-title">
            <h1>AuraCRM</h1>
            <p>HCP Engagement Module</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={fetchData} style={{ padding: '8px 12px' }}>
            <RefreshCw size={16} />
          </button>
          <div className="chat-status">
            <span className="status-dot"></span>
            <span>Agent Active (Groq Gemma2/Llama)</span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="main-content">
        {/* Left: Structured Form */}
        <div className="glass-panel form-container">
          <div className="section-title">
            <Activity size={18} className="text-indigo-400" />
            <h2>{editingId ? "Edit HCP Interaction" : "Log HCP Interaction"}</h2>
          </div>

          <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="form-grid">
              {/* HCP Search/Select */}
              <div className="form-group">
                <label>HCP Name *</label>
                <select 
                  name="hcp_id" 
                  value={formData.hcp_id} 
                  onChange={handleInputChange}
                  required
                >
                  <option value="">Select or search HCP...</option>
                  {hcps.map(h => (
                    <option key={h.id} value={h.id}>
                      {h.name} ({h.specialty} - {h.clinic})
                    </option>
                  ))}
                </select>
              </div>

              {/* Interaction Type */}
              <div className="form-group">
                <label>Interaction Type</label>
                <select 
                  name="interaction_type" 
                  value={formData.interaction_type} 
                  onChange={handleInputChange}
                >
                  <option value="Meeting">Meeting</option>
                  <option value="Call">Phone Call</option>
                  <option value="Email">Email</option>
                  <option value="Video Call">Video Call</option>
                </select>
              </div>

              {/* Date */}
              <div className="form-group">
                <label>Date</label>
                <input 
                  type="date" 
                  name="date" 
                  value={formData.date} 
                  onChange={handleInputChange}
                  required 
                />
              </div>

              {/* Time */}
              <div className="form-group">
                <label>Time</label>
                <input 
                  type="time" 
                  name="time" 
                  value={formData.time} 
                  onChange={handleInputChange}
                  required 
                />
              </div>

              {/* Attendees */}
              <div className="form-group full-width">
                <label>Attendees (comma separated)</label>
                <input 
                  type="text" 
                  name="attendees" 
                  placeholder="e.g. Dr. Emily Smith, Representative Jack" 
                  value={formData.attendees} 
                  onChange={handleInputChange}
                />
              </div>

              {/* Topics Discussed */}
              <div className="form-group full-width">
                <label>Topics Discussed</label>
                <textarea 
                  name="topics_discussed" 
                  rows="3" 
                  placeholder="Enter key discussion points..."
                  value={formData.topics_discussed} 
                  onChange={handleInputChange}
                />
              </div>

              {/* Materials Shared */}
              <div className="form-group full-width">
                <label>Materials Shared / Samples Distributed</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '4px' }}>
                  {/* Materials list */}
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', border: '1px solid var(--bg-card-border)' }}>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 'bold' }}>MARKETING MATERIALS</p>
                    {materials.filter(m => m.type === "Material").map(m => (
                      <label key={m.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', color: 'var(--text-main)' }}>
                        <input 
                          type="checkbox" 
                          checked={formData.materials_shared.includes(m.name)} 
                          onChange={(e) => handleCheckboxChange("materials_shared", m.name, e.target.checked)}
                        />
                        <span>{m.name}</span>
                      </label>
                    ))}
                  </div>
                  {/* Samples list */}
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', border: '1px solid var(--bg-card-border)' }}>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 'bold' }}>DRUG SAMPLES</p>
                    {materials.filter(m => m.type === "Sample").map(m => (
                      <label key={m.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', color: 'var(--text-main)' }}>
                        <input 
                          type="checkbox" 
                          checked={formData.samples_distributed.includes(m.name)} 
                          onChange={(e) => handleCheckboxChange("samples_distributed", m.name, e.target.checked)}
                          disabled={m.stock <= 0}
                        />
                        <span>{m.name} <span style={{ color: 'var(--accent-secondary)', fontSize: '11px' }}>({m.stock} left)</span></span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              {/* Observed HCP Sentiment */}
              <div className="form-group full-width">
                <label>Observed/Inferred HCP Sentiment</label>
                <div className="sentiment-group">
                  <div 
                    className={`sentiment-btn ${formData.sentiment === 'Positive' ? 'active positive' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, sentiment: 'Positive' }))}
                  >
                    <ThumbsUp size={16} /> Positive
                  </div>
                  <div 
                    className={`sentiment-btn ${formData.sentiment === 'Neutral' ? 'active neutral' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, sentiment: 'Neutral' }))}
                  >
                    <Meh size={16} /> Neutral
                  </div>
                  <div 
                    className={`sentiment-btn ${formData.sentiment === 'Negative' ? 'active negative' : ''}`}
                    onClick={() => setFormData(prev => ({ ...prev, sentiment: 'Negative' }))}
                  >
                    <ThumbsDown size={16} /> Negative
                  </div>
                </div>
              </div>

              {/* Outcomes */}
              <div className="form-group full-width">
                <label>Key Outcomes / Agreements</label>
                <textarea 
                  name="outcomes" 
                  rows="2" 
                  placeholder="Key outcomes or agreements..."
                  value={formData.outcomes} 
                  onChange={handleInputChange}
                />
              </div>

              {/* Follow-up Actions */}
              <div className="form-group full-width">
                <label>Follow-up Actions / Next Steps</label>
                <input 
                  type="text" 
                  name="follow_up_actions" 
                  placeholder="e.g. Schedule follow-up meeting in 2 weeks" 
                  value={formData.follow_up_actions} 
                  onChange={handleInputChange}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                <CheckSquare size={16} />
                {editingId ? "Update Interaction" : "Log Interaction"}
              </button>
              {editingId && (
                <button type="button" className="btn btn-secondary" onClick={resetForm}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Right: AI Assistant Conversational Chat */}
        <div className="glass-panel chat-container">
          <div className="chat-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} style={{ color: 'var(--accent-secondary)' }} />
              <h2 style={{ fontSize: '16px', fontWeight: 600 }}>AI Assistant</h2>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>LangGraph Powered</span>
          </div>

          <div className="chat-messages">
            {chat.messages.map((m, idx) => (
              <div key={idx} className={`chat-msg ${m.role}`}>
                {m.content}
              </div>
            ))}
            {chat.loading && (
              <div className="chat-msg assistant" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div className="spinner"></div>
                <span>Extracting information...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Sync form banner if AI extracted something */}
          {chat.extractedForm && Object.keys(chat.extractedForm).length > 0 && (
            <div className="sync-alert">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertCircle size={14} />
                <span>AI extracted fields for <strong>{chat.extractedForm.hcp_name || `HCP ID ${chat.extractedForm.hcp_id}`}</strong>.</span>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button 
                  onClick={applyAIExtractedForm} 
                  style={{ background: '#22d3ee', color: '#0f172a', border: 'none', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
                >
                  Sync Form
                </button>
                <button 
                  onClick={() => dispatch(clearExtractedForm())} 
                  style={{ background: 'transparent', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.2)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Suggestions */}
          <div className="chat-suggestions">
            <span 
              className="suggestion-pill"
              onClick={() => handleSendMessage("Search doctors with Oncology specialty")}
            >
              🔍 Search Oncology
            </span>
            <span 
              className="suggestion-pill"
              onClick={() => handleSendMessage("Log meeting with Dr. Emily Smith, discussed OncoBoost PDF, positive response, follow-up next week")}
            >
              ✍️ Log Emily Smith meeting
            </span>
            <span 
              className="suggestion-pill"
              onClick={() => handleSendMessage("List available materials and samples")}
            >
              📋 List samples
            </span>
          </div>

          {/* Chat Input */}
          <div className="chat-input-area">
            <input 
              type="text" 
              className="chat-input"
              placeholder="Describe interaction or ask a question..." 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            />
            <button className="btn btn-primary" onClick={() => handleSendMessage()} style={{ padding: '10px 14px' }}>
              <Send size={16} />
            </button>
          </div>
        </div>

        {/* Lower: Logged Interactions List */}
        <div className="glass-panel list-panel">
          <div className="section-title">
            <FileSpreadsheet size={18} className="text-cyan-400" />
            <h2>Logged Interactions</h2>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>HCP Name</th>
                  <th>Type</th>
                  <th>Date & Time</th>
                  <th>Discussed</th>
                  <th>Materials & Samples</th>
                  <th>Sentiment</th>
                  <th>Follow-ups</th>
                  <th style={{ width: '100px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {interactions.length === 0 ? (
                  <tr>
                    <td colSpan="8" style={{ textAlignment: 'center', color: 'var(--text-muted)', padding: '20px' }}>
                      No interactions logged yet. Complete the form above or tell the AI Assistant to log one.
                    </td>
                  </tr>
                ) : (
                  interactions.map(item => (
                    <tr key={item.id}>
                      <td style={{ fontWeight: 600 }}>{item.hcp_name}</td>
                      <td>
                        <span style={{ fontSize: '12px', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                          {item.interaction_type}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
                          <Clock size={10} />
                          <span>{item.date} {item.time}</span>
                        </div>
                      </td>
                      <td style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={item.topics_discussed}>
                        {item.topics_discussed}
                      </td>
                      <td>
                        <div>
                          {item.materials_shared ? item.materials_shared.split(", ").map((m, i) => (
                            <span key={i} className="material-tag">{m}</span>
                          )) : null}
                          {item.samples_distributed ? item.samples_distributed.split(", ").map((s, i) => (
                            <span key={i} className="sample-tag">{s}</span>
                          )) : null}
                        </div>
                      </td>
                      <td>
                        <span className={`sentiment-badge ${item.sentiment.toLowerCase()}`}>
                          {item.sentiment}
                        </span>
                      </td>
                      <td style={{ fontSize: '12px', color: 'var(--accent-secondary)' }}>
                        {item.follow_up_actions}
                      </td>
                      <td>
                        <div className="actions-cell">
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '6px' }}
                            onClick={() => startEdit(item)}
                          >
                            <Edit3 size={14} />
                          </button>
                          <button 
                            className="btn btn-danger" 
                            style={{ padding: '6px' }}
                            onClick={() => handleDelete(item.id)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
