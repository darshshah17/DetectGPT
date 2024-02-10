import torch
import re
import spacy
from transformers import GPT2LMHeadModel, GPT2TokenizerFast
from collections import OrderedDict



class GPT2PPL:
    def __init__(self, device="cpu", model_id="gpt2"):
        self.device = device
        self.model_id = model_id
        self.model = GPT2LMHeadModel.from_pretrained(model_id).to(device)
        self.tokenizer = GPT2TokenizerFast.from_pretrained(model_id)
        self.nlp = spacy.load("en_core_web_sm") 

        self.max_length = self.model.config.n_positions
        self.stride = 512
        
    def getResults(self, threshold):
        if threshold < 70:
            label = 0
            return "The Text is likely generated by AI.", label
        elif threshold < 85:
            label = 0
            return "The Text is most probably contain parts which are generated by AI. (require more text for better Judgement)", label
        else:
            label = 1
            return "The Text is likely written by Human.", label

    # def is_valid_word(self, word):
    #     """
    #     Check if a word is a valid English word using spaCy.
    #     """
    #     return word.lower() in self.nlp.vocab

    # def check_valid_words(self, sentence):
    #     """
    #     Check if all words in the sentence are valid English words.
    #     """
    #     words = re.findall(r'\b\w+\b', sentence)
    #     invalid_words = [word for word in words if not self.is_valid_word(word)]
    #     return invalid_words
    
    def __call__(self, sentence):
        results = OrderedDict()

        total_valid_char = re.findall("[a-zA-Z0-9]+", sentence)
        total_valid_char = sum([len(x) for x in total_valid_char])

        if total_valid_char < 100:
            return {"status": "Please input more text (min 100 characters)"}, "Please input more text (min 100 characters)"

        # invalid_words = self.check_valid_words(sentence)
        # if invalid_words:
        #     return {"status": "Input contains invalid words."}, "Input contains invalid words."

        lines = re.split(r'(?<=[.?!][ \[\(])|(?<=\n)\s*', sentence)
        lines = list(filter(lambda x: (x is not None) and (len(x) > 0), lines))

        ppl = self.getPPL(sentence)
        print(f"Perplexity {ppl}")
        results["Perplexity"] = ppl

        offset = ""
        Perplexity_per_line = []
        for i, line in enumerate(lines):
            if re.search("[a-zA-Z0-9]+", line) == None:
                continue
            if len(offset) > 0:
                line = offset + line
                offset = ""
            if line[0] == "\n" or line[0] == " ":
                line = line[1:]
            if line[-1] == "\n" or line[-1] == " ":
                line = line[:-1]
            elif line[-1] == "[" or line[-1] == "(":
                offset = line[-1]
                line = line[:-1]
            ppl = self.getPPL(line)
            Perplexity_per_line.append(ppl)

        results["Perplexity per line"] = sum(Perplexity_per_line) / len(Perplexity_per_line)
        results["Burstiness"] = max(Perplexity_per_line)

        out, label = self.getResults(results["Perplexity per line"])
        results["label"] = label

        return results, out

    def getPPL(self,sentence):
        encodings = self.tokenizer(sentence, return_tensors="pt")
        seq_len = encodings.input_ids.size(1)

        nlls = []
        likelihoods = []
        prev_end_loc = 0
        for begin_loc in range(0, seq_len, self.stride):
            end_loc = min(begin_loc + self.max_length, seq_len)
            trg_len = end_loc - prev_end_loc
            input_ids = encodings.input_ids[:, begin_loc:end_loc].to(self.device)
            target_ids = input_ids.clone()
            target_ids[:, :-trg_len] = -100

            with torch.no_grad():
                outputs = self.model(input_ids, labels=target_ids)
                neg_log_likelihood = outputs.loss * trg_len
                likelihoods.append(neg_log_likelihood)

            nlls.append(neg_log_likelihood)

            prev_end_loc = end_loc
            if end_loc == seq_len:
                break
        ppl = int(torch.exp(torch.stack(nlls).sum() / end_loc))
        return ppl