import React, { createContext, useContext, useState } from "react";

const MentorContext = createContext();

export const MentorProvider = ({ children }) => {
    const [mentors, setMentors] = useState({});

    const saveMentor = (key, mentor) => {
    setMentors(prev => ({ ...prev, [key]: mentor }));
    };

    const getMentor = (key) => {
    return mentors[key] || null;
    };
    
    return (
        <MentorContext.Provider value={{ mentors, saveMentor, getMentor }}>
        {children}
        </MentorContext.Provider>
    );
};

export const useMentor = () => useContext(MentorContext);
