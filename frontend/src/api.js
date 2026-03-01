import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:5000",
});

export const generateNote = async (transcript) => {
  return await API.post("/generate-note", {
    transcript,
  });
};