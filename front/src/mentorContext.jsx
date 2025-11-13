import React, { createContext, useContext, useState } from "react";

const MentorContext = createContext();

export const MentorProvider = ({ children }) => {
    const [mentor, setMentor] = useState(null);
    return (
        <MentorContext.Provider value={{ mentor, setMentor }}>
        {children}
        </MentorContext.Provider>
    );
};

export const useMentor = () => useContext(MentorContext);
