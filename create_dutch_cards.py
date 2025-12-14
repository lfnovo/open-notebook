import asyncio
from api.anki_service import AnkiService
import json


async def main():
    svc = AnkiService()
    deck = await svc.create_deck(
        name='Dutch B2 - Comprehensive', 
        description='Multi-angle vocabulary cards for B2 learners'
    )
    did = str(deck.id)
    
    # Card 1: Translation
    c1 = await svc.create_card(
        front='Wat betekent "verhuizen" in het Engels?',
        back='to move (house), to relocate',
        notes='Common verb. Present: ik verhuis, jij verhuist. Past: ik verhuisde. Example: We zijn vorige maand verhuisd naar Amsterdam.',
        deck_id=did,
        tags=['dutch', 'B2', 'verbs', 'housing', 'translation']
    )
    
    # Card 2: Image/Context Association
    c2 = await svc.create_card(
        front='Je ziet dozen, een verhuiswagen en mensen die meubels dragen. Welk werkwoord past hierbij?',
        back='verhuizen',
        notes='Visual context: moving house scenario with boxes, moving truck, furniture.',
        deck_id=did,
        tags=['dutch', 'B2', 'visual-context', 'housing']
    )
    
    # Card 3: Related Words (Word Family)
    c3 = await svc.create_card(
        front='Wat zijn verwante woorden van "verhuizen"?',
        back='de verhuizing (the move), de verhuizer (mover), het verhuisbedrijf (moving company), de verhuiswagen (moving truck)',
        notes='Word family: verhuis- prefix appears in related concepts.',
        deck_id=did,
        tags=['dutch', 'B2', 'word-family', 'housing']
    )
    
    # Card 4: False Friends
    c4 = await svc.create_card(
        front='Let op: "verhuizen" betekent NIET "to house" of "to rent". Wat betekent het wel?',
        back='to move (house), to relocate from one residence to another',
        notes='False friend alert: Despite containing "huis" (house), it means changing residence, not providing housing. For renting use "huren".',
        deck_id=did,
        tags=['dutch', 'B2', 'false-friends', 'housing']
    )
    
    # Card 5: Synonyms/Register
    c5 = await svc.create_card(
        front='Wat is een formeler synoniem voor "verhuizen"?',
        back='verplaatsen (to relocate), zijn woonplaats veranderen (to change one\'s place of residence)',
        notes='Register: "verhuizen" is neutral/informal. In formal contexts: "zijn domicilie verplaatsen" (legal register).',
        deck_id=did,
        tags=['dutch', 'B2', 'register', 'synonyms']
    )
    
    # Card 6: Conversation Context
    c6 = await svc.create_card(
        front='Vul in: "Wanneer ben je ___? Ik wil je helpen met inpakken."',
        back='aan het verhuizen / van plan te verhuizen',
        notes='Conversational usage: "Wanneer verhuis je?" (When are you moving?) or "Ik ben volgende week aan het verhuizen" (I\'m moving next week).',
        deck_id=did,
        tags=['dutch', 'B2', 'conversation', 'housing']
    )
    
    # Card 7: Collocations (Prepositions)
    c7 = await svc.create_card(
        front='Welke voorzetsel gebruik je: "verhuizen ___ een nieuwe stad"?',
        back='naar (verhuizen naar)',
        notes='Collocation: verhuizen + naar (to move to). Example: We verhuizen naar Groningen. NOT "verhuizen in" or "verhuizen op".',
        deck_id=did,
        tags=['dutch', 'B2', 'collocations', 'prepositions']
    )
    
    # Card 8: Homonyms/Similar Sounds
    c8 = await svc.create_card(
        front='Wat is het verschil tussen "verhuizen" en "verhuren"?',
        back='verhuizen = to move (house), verhuren = to rent out (as landlord)',
        notes='Sound-alike pair: verhuizen (moving) vs verhuren (renting out property). Example: Hij verhuurt zijn oude huis omdat hij verhuist naar het buitenland.',
        deck_id=did,
        tags=['dutch', 'B2', 'homonyms', 'housing', 'confusables']
    )
    
    cards = [c1, c2, c3, c4, c5, c6, c7, c8]
    result = [
        {
            'type': card.tags[-1] if 'translation' in card.tags else (
                'visual-context' if 'visual-context' in card.tags else
                'word-family' if 'word-family' in card.tags else
                'false-friends' if 'false-friends' in card.tags else
                'synonyms' if 'synonyms' in card.tags else
                'conversation' if 'conversation' in card.tags else
                'collocations' if 'collocations' in card.tags else
                'homonyms' if 'homonyms' in card.tags else 'other'
            ),
            'front': card.front,
            'back': card.back,
            'tags': card.tags
        } 
        for card in cards
    ]
    
    print(json.dumps({
        'deck_id': did,
        'deck_name': deck.name,
        'cards_created': len(cards),
        'card_types': ['translation', 'visual-context', 'word-family', 'false-friends', 'synonyms', 'conversation', 'collocations', 'homonyms'],
        'cards': result
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
