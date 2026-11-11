"""Edit decision list for 'From Dinosaurs to Humans'.  python3 edl.py lines_dur.json -> shots.json + voice placement (voice.json)
Each shot: (id, world, lines spoken in it, extra seconds of pure picture, description).  Lines start LEAD s into the shot
(or right after the previous line of the same shot + GAP); the shot ends TAIL s after its last line (or after `extra`)."""
import json, sys, os

LEAD, GAP, TAIL = .45, .35, .4
S = [
 # --- 1 classroom
 ('c01', 'classroom', [], 3.6, 'wide: sunny classroom, bored students: Rohan asleep on his desk, a girl stabbing a pencil into an eraser'),
 ('c02', 'classroom', [], 3.0, 'teacher writes EVOLUTION OF LIFE ON EARTH on the green board (chalk squeak)'),
 ('c03', 'classroom', ['L000'], 0, 'teacher turns around, already tired: Alright class...'),
 ('c04', 'classroom', ['L001'], 0, 'Kevin raises his hand, confident: does that mean humans came from dinosaurs?'),
 ('c05', 'classroom', [], 2.6, 'teacher slowly removes his glasses. silence. a cricket gives up'),
 ('c06', 'classroom', ['L002'], 0, 'teacher: No, Kevin...'),
 ('c07', 'classroom', [], 2.2, 'students laugh; Kevin laughs a second late'),
 ('c08', 'classroom', [], 2.6, 'teacher draws a big chalk T-rex - annoyingly good'),
 ('c09', 'classroom', ['L003'], 0, 'teacher: millions of years ago this planet belonged to creatures...'),
 ('c10', 'classroom', [], 3.6, 'slow push toward the chalk dinosaur; Kevin stares; the chalk eye BLINKS'),
 ('c11', 'classroom', [], 2.8, 'Kevin looks at the teacher (not looking), back at the board: it blinks again'),
 ('c12', 'classroom', ['L004'], 0, 'sounds fade; narrator; camera pushes INTO the board, chalk dust turns into real dinosaur skin'),
 ('c13', 'young_earth', [], 3.0, 'ROAR. the camera flies through the dinosaur eye and comes out over a lava-covered planet'),
 # --- 2 young Earth
 ('e01', 'young_earth', ['L005'], 0, 'drone sweep over the hostile young Earth: volcanoes, lava, boiling sea, orange clouds'),
 ('e02', 'young_earth', ['L006'], 0, 'meteors hammer the surface, volcanoes erupt'),
 ('e03', 'young_earth', [], 2.2, 'a meteor crashes into the ocean - huge splash'),
 ('e04', 'young_earth', ['L007'], 2.0, 'cartoon guy in a tiny beach chair, sunglasses, sipping a drink while lava rains; the drink catches fire, he keeps sipping'),
 ('e05', 'young_earth', ['L008'], 0, 'time-lapse: the planet cools, the oceans settle'),
 ('e06', 'microbes', [], 2.0, 'the camera dives beneath the ocean surface'),
 ('e07', 'microbes', ['L009'], 0, 'microscopic world: bacteria drifting in ancient water'),
 ('e08', 'microbes', ['L010'], 0, 'one bumps into another. neither apologizes'),
 # --- 3 photosynthesis
 ('m01', 'shallows', ['L011'], 0, 'cyanobacteria mats soaking up sunlight in shallow water, looking pleased'),
 ('m02', 'shallows', ['L012'], 0, 'oxygen bubbles rising from the microbial mats, sky slowly turning blue'),
 ('m03', 'shallows', ['L013'], 0, 'the screen fills with oxygen molecules; oxygen-hating microbes shrivel'),
 ('m04', 'classroom', ['L014'], 0, 'classroom: teacher - the smallest things make the biggest difference'),
 ('m05', 'classroom', ['L015'], 2.2, 'Rohan wakes up: Like homework, sir? teacher stares; Rohan slowly lowers his head back onto the desk'),
 ('m06', 'ediacaran', ['L016'], 0, 'cells clump into multicellular life; Dickinsonia - a pancake and a pillow had a baby'),
 # --- 4 Cambrian
 ('k01', 'cambrian', ['L017'], 0, 'the camera races through a crowded ancient ocean - the Cambrian explosion'),
 ('k02', 'cambrian', ['L018'], 0, 'trilobites, Hallucigenia, sponges: a dangerous playground'),
 ('k03', 'cambrian', ['L019'], 0, 'Anomalocaris swims straight toward the camera'),
 ('k04', 'cambrian', [], 2.6, 'Anomalocaris opens its mouth; a tiny cartoon fish gasps and reverses at top speed'),
 ('k05', 'cambrian', ['L020'], 0, 'arms race: predators chase, prey hides'),
 ('k06', 'devonian_sea', ['L021'], 0, 'a fish with brand-new jaws looks proud and bites the nearest rock'),
 # --- 5 onto land
 ('l01', 'coast', ['L022'], 0, 'the camera rises out of the water to a coastline carpeted with early plants'),
 ('l02', 'coast', ['L023'], 0, 'early land arthropods crawl across the rocks'),
 ('l03', 'coast', ['L024'], 0, 'a lobe-finned fish paddles in the shallows on thick fleshy fins'),
 ('l04', 'coast', ['L025'], 0, 'Tiktaalik hauls itself through the mud, gets stuck, stares at the camera'),
 ('l05', 'classroom', ['L026', 'L027', 'L028'], 0, 'classroom: Priya - ancient fish technology? I want a refund'),
 # --- 6 extinction + rise of the dinosaurs
 ('p01', 'permian', ['L029'], 0, 'a lush ancient forest; timeline slam: 252 MILLION YEARS AGO - PERMIAN MASS EXTINCTION'),
 ('p02', 'permian', ['L030'], 0, 'volcanic eruptions, collapsing ecosystems, a changing climate'),
 ('p03', 'black', [], 2.2, 'fade to black. silence'),
 ('p04', 'triassic', ['L031'], 0, 'a new ecosystem fades in'),
 ('p05', 'triassic', ['L032'], 0, 'small early dinosaurs dart through the forest - nervous chickens'),
 ('p06', 'jurassic', ['L033'], 0, 'time-lapse across Triassic, Jurassic, Cretaceous: dinosaurs grow bigger'),
 ('p07', 'jurassic', ['L034'], 0, 'a giant sauropod walks through the forest; the ground shakes; birds scatter'),
 ('p08', 'jurassic', ['L035'], 0, 'Stegosaurus in a Jurassic forest; then Triceratops and a T-rex in a later Cretaceous landscape'),
 ('p09', 'split', [], 3.0, 'split screen across a gap in time: the Stegosaurus waves goodbye; the T-rex has no idea who he is'),
 ('p10', 'cretaceous', ['L036'], 0, 'Mesozoic panorama'),
 ('p11', 'cretaceous', [], 2.6, 'T-rex roars directly into the camera'),
 ('p12', 'classroom', ['L037', 'L038'], 0, 'classroom: Kevin - class pet? teacher - attendance above fifty percent'),
 # --- 7 dinosaurs rule
 ('d01', 'jurassic', ['L039'], 0, 'drone: a herd of enormous sauropods crosses a valley'),
 ('d02', 'coast_cretaceous', ['L040'], 0, 'pterosaurs glide over the coastline; caption NOT A DINOSAUR'),
 ('d03', 'cretaceous', ['L041'], 0, 'a pack of small theropods sprints through a forest; a T-rex hunts'),
 ('d04', 'cretaceous', ['L042'], 0, 'a feathered dinosaur shakes out its feathers like a wet dog'),
 ('d05', 'cretaceous', ['L043', 'L044'], 0, 'a small bird lands on a giant dinosaur head; the dinosaur does not react'),
 ('d06', 'classroom', ['L045', 'L046'], 0, 'classroom: Sam - pigeon attack? teacher - the pigeon usually wins'),
 # --- 8 the asteroid
 ('a01', 'cretaceous', ['L047'], 0, 'peaceful Cretaceous: dinosaurs graze, a dragonfly lands on a Triceratops'),
 ('a02', 'cretaceous', ['L048'], 0, 'a bright dot appears in the sky - slow cinematic zoom'),
 ('a03', 'impact', [], 2.8, 'the asteroid enters the atmosphere; the sky glows orange; white flash'),
 ('a04', 'impact', ['L049'], 0, 'impact: fireball, shockwave, earthquakes, a wall of dust'),
 ('a05', 'impact', ['L050'], 0, 'forests burn, the sky goes dark, dinosaurs struggle in the cold'),
 ('a06', 'impact', ['L051'], 0, 'a bird flies calmly out of the smoke'),
 ('a07', 'impact', ['L052'], 0, 'the camera pans down through the smoke to a tiny mammal under fallen leaves, blinking'),
 # --- 9 mammals
 ('n01', 'paleogene', ['L053'], 0, 'small early mammals scurry through the forest'),
 ('n02', 'paleogene', ['L054'], 0, 'mammals spread: grasslands, oceans, bats in the sky'),
 ('n03', 'paleogene', [], 3.0, 'a tiny mammal looks up at a giant dinosaur skeleton, checks both ways, walks off with confidence'),
 ('n04', 'paleogene', ['L055', 'L056'], 0, 'an ancient primate climbs a tree, grasping hands, forward-facing eyes'),
 ('n05', 'classroom', ['L057', 'L058', 'L059', 'L060'], 0, 'classroom: Kevin - monkeys? cousins? teacher - stop asking about the T-rex'),
 # --- 10 humans
 ('h01', 'savanna', ['L061'], 0, 'a primate in the forest transitions across millions of years to the African savanna'),
 ('h02', 'savanna', ['L062'], 0, 'a branching family tree of hominins'),
 ('h03', 'savanna', ['L063'], 0, 'Australopithecus walks upright across the savanna'),
 ('h04', 'savanna', ['L064'], 0, 'early Homo knapping stone tools'),
 ('h05', 'cave', ['L065'], 0, 'a Neanderthal gives a thumbs-up from a cave'),
 ('h06', 'savanna', ['L066'], 0, 'early Homo sapiens appear'),
 ('h07', 'cave', ['L067'], 0, 'humans making tools, hunting, communicating, painting animals on a cave wall'),
 ('h08', 'city', ['L068'], 0, 'ancient settlements transform into modern cities'),
 # --- 11 caves to smartphones
 ('t01', 'city', ['L069'], 0, 'time-lapse: stone tools to metal, villages to cities to skyscrapers'),
 ('t02', 'cave', [], 4.2, 'a caveman pokes a smartphone; it lights up; he screams, throws it, then slowly picks it back up'),
 ('t03', 'space', ['L070'], 0, 'a rocket launches into space'),
 ('t04', 'livingroom', ['L071'], 0, 'a human on a sofa scrolling, dead-eyed; a cat falls off a table on the phone'),
 ('t05', 'montage', [], 3.0, 'montage: medicine, satellites, space - then a cat falls off a table; the human laughs'),
 ('t06', 'savanna', ['L072'], 0, 'evolution did not stop'),
 ('t07', 'montage', ['L073'], 0, 'life keeps changing: populations adapt'),
 # --- 12 back to class
 ('b01', 'classroom', [], 3.0, 'the camera flies backward through the dinosaur eye; it becomes chalk; Kevin staring, mouth open'),
 ('b02', 'classroom', ['L074'], 1.0, 'teacher: so, class...'),
 ('b03', 'classroom', ['L075', 'L076', 'L077'], 0, 'Kevin: we still have to do homework?'),
 ('b04', 'classroom', [], 3.0, 'the teacher drops an enormous stack of notebooks; the room shakes; a pencil rolls off'),
 ('b05', 'classroom', ['L078'], 0, 'teacher: evolution did not make you exempt from homework'),
 ('b06', 'classroom', [], 3.0, 'the class groans; Rohan wakes, sees the stack, goes back to sleep out of principle'),
 ('b07', 'classroom', ['L079'], 0, 'narrator over the class'),
 ('b08', 'space', ['L080', 'L081'], 0, 'the camera pulls out through the classroom window: Earth from space, calm and blue'),
 ('b09', 'space', [], 4.5, 'END CARD: LIFE IS STILL EVOLVING. (And so is Kevin\'s homework.)'),
]


def build(lines_json, out_dir):
    L = {l['id']: l for l in json.load(open(lines_json))}
    t = 0.0; shots = []; voice = []
    for sid, world, lids, extra, desc in S:
        t0 = t; cur = t0 + LEAD
        for k, lid in enumerate(lids):
            if k: cur += GAP
            voice.append(dict(id=lid, t=round(cur, 3), who=L[lid]['who'])); cur += L[lid]['dur']
        end = (cur + TAIL) if lids else t0
        end = max(end + extra, t0 + 1.2)
        shots.append(dict(id=sid, world=world, t0=round(t0, 3), dur=round(end - t0, 3), desc=desc, lines=lids))
        if world == 'split':                  # two halves rendered separately, stacked side by side in compose
            shots[-1]['render'] = False; shots[-1]['parts'] = [sid + 'a', sid + 'b']
            for pid, pw in ((sid + 'a', 'jurassic'), (sid + 'b', 'cretaceous')):
                shots.append(dict(id=pid, world=pw, t0=round(t0, 3), dur=round(end - t0, 3), desc=desc + ' (half)', lines=[], part_of=sid))
        t = end
    json.dump(dict(fps=24, w=1920, h=1080, total=round(t, 2), voice='voice.wav', trans={}, subs=[], shots=shots), open(os.path.join(out_dir, 'shots.json'), 'w'), indent=1)
    json.dump(voice, open(os.path.join(out_dir, 'voice.json'), 'w'), indent=1)
    print('shots', len(shots), 'total', round(t / 60, 2), 'min')


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lines.json'), os.path.dirname(os.path.abspath(__file__)))
