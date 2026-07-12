import { configureStore, createSlice } from '@reduxjs/toolkit'

// Slice for HCPs
const hcpSlice = createSlice({
  name: 'hcps',
  initialState: { list: [], loading: false, error: null },
  reducers: {
    setHcpsStart(state) { state.loading = true; },
    setHcpsSuccess(state, action) { state.list = action.payload; state.loading = false; },
    setHcpsFailure(state, action) { state.error = action.payload; state.loading = false; }
  }
})

// Slice for Materials
const materialsSlice = createSlice({
  name: 'materials',
  initialState: { list: [], loading: false, error: null },
  reducers: {
    setMaterialsStart(state) { state.loading = true; },
    setMaterialsSuccess(state, action) { state.list = action.payload; state.loading = false; },
    setMaterialsFailure(state, action) { state.error = action.payload; state.loading = false; },
    updateStock(state, action) {
      const { name, amount } = action.payload;
      const item = state.list.find(i => i.name.toLowerCase() === name.toLowerCase());
      if (item && item.stock > 0) {
        item.stock = Math.max(0, item.stock - amount);
      }
    }
  }
})

// Slice for Interactions
const interactionsSlice = createSlice({
  name: 'interactions',
  initialState: { list: [], loading: false, error: null },
  reducers: {
    setInteractionsStart(state) { state.loading = true; },
    setInteractionsSuccess(state, action) { state.list = action.payload; state.loading = false; },
    setInteractionsFailure(state, action) { state.error = action.payload; state.loading = false; },
    addInteraction(state, action) {
      state.list.unshift(action.payload);
    },
    updateInteraction(state, action) {
      const idx = state.list.findIndex(i => i.id === action.payload.id);
      if (idx !== -1) {
        state.list[idx] = action.payload;
      }
    },
    removeInteraction(state, action) {
      state.list = state.list.filter(i => i.id !== action.payload);
    }
  }
})

// Slice for Chat
const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      { role: 'assistant', content: 'Hello! I am your AI CRM Assistant. You can describe your interaction in detail here (e.g. "I met with Dr. Emily Smith today to discuss OncoBoost Phase III and handed out 1 starter kit. The feedback was very positive!"). I will extract the details and log them automatically.' }
    ],
    loading: false,
    extractedForm: {}
  },
  reducers: {
    addMessage(state, action) {
      state.messages.push(action.payload);
    },
    setChatLoading(state, action) {
      state.loading = action.payload;
    },
    setExtractedForm(state, action) {
      state.extractedForm = action.payload;
    },
    clearExtractedForm(state) {
      state.extractedForm = {};
    }
  }
})

export const { setHcpsStart, setHcpsSuccess, setHcpsFailure } = hcpSlice.actions
export const { setMaterialsStart, setMaterialsSuccess, setMaterialsFailure, updateStock } = materialsSlice.actions
export const { setInteractionsStart, setInteractionsSuccess, setInteractionsFailure, addInteraction, updateInteraction, removeInteraction } = interactionsSlice.actions
export const { addMessage, setChatLoading, setExtractedForm, clearExtractedForm } = chatSlice.actions

const store = configureStore({
  reducer: {
    hcps: hcpSlice.reducer,
    materials: materialsSlice.reducer,
    interactions: interactionsSlice.reducer,
    chat: chatSlice.reducer
  }
})

export default store
