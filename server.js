import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import dotenv from 'dotenv';
import authRoutes from './routes/auth.js';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

// Handle __dirname in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config();

// Create Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Add cache control headers
app.use((req, res, next) => {
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  res.set('Expires', '-1');
  res.set('Pragma', 'no-cache');
  next();
});

// Connect to MongoDB
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/campus-genie', {
  useNewUrlParser: true,
  useUnifiedTopology: true
})
.then(() => console.log('MongoDB connected successfully'))
.catch(err => console.error('MongoDB connection error:', err));

// Serve static assets
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.static(path.join(__dirname, 'dist')));

// API Routes
app.use('/api/auth', authRoutes);

// Serve dashboard data from kmit_data.json
app.get('/api/dashboard-data', (req, res) => {
  try {
    const dataPath = path.join(__dirname, 'kmit_data.json');
    if (fs.existsSync(dataPath)) {
      const fileData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
      const stats = fs.statSync(dataPath);
      res.json({
        attendance: {
          timestamp: stats.mtime.toLocaleString(),
          sessions: fileData.sessions || []
        },
        timetable: fileData.timetable || []
      });
    } else {
      res.json({
        attendance: {
          timestamp: 'No data',
          sessions: []
        },
        timetable: []
      });
    }
  } catch (error) {
    console.error('Error reading dashboard data:', error);
    res.status(500).json({ error: 'Failed to read dashboard data' });
  }
});

// Serve the React app
app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
});

// Start server
const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

