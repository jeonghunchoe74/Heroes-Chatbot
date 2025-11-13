import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { MentorProvider } from "./mentorContext";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <MentorProvider>
      <App />
    </MentorProvider>
  </React.StrictMode>
);
