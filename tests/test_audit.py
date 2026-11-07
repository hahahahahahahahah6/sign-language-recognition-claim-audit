import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from sign_language_recognition_claim_audit.audit import claims, has_evidence
from sign_language_recognition_claim_audit.phrases import SIGNLANGUAGE, NOSIGNLANGUAGE, GENERIC_NAMES, DEDICATED_CLASSES

class AuditTests(unittest.TestCase):
    def test_positive_oracle(self):
        self.assertEqual(SIGNLANGUAGE, ['sign language recognition', 'sign-language recognition', 'signlanguage recognition', 'recognize sign language', 'recognizes sign language', 'recognizing sign language', 'recognised sign language', 'sign language translation', 'translate sign language', 'translates sign language', 'translating sign language', 'sign language interpreter', 'sign language interpreters', 'sign language interpretation', 'sign language detection', 'detect sign language', 'detects sign language', 'sign language understanding', 'understand sign language', 'sign language transcription', 'transcribe sign language', 'sign language to text', 'sign to text', 'asl recognition', 'american sign language recognition', 'asl translation', 'fingerspelling recognition', 'recognize fingerspelling', 'sign language classifier', 'sign language classifiers', 'sign language model', 'sign language models', 'sign language system', 'sign language tool', 'sign language feature', 'sign language support', 'supports sign language recognition', 'sign language capability', 'sign language api', 'sign language framework', 'sign language library', 'sign language pipeline', 'sign language engine', 'sign language module', 'sign language function', 'sign language functionality', 'sign language algorithm', 'sign language algorithms', 'sign language dataset', 'sign language task'])

    def test_negative_oracle(self):
        self.assertEqual(NOSIGNLANGUAGE, ['does not recognize sign language', 'do not recognize sign language', "doesn't recognize sign language", "don't recognize sign language", 'no sign language recognition', 'without sign language recognition', 'never recognizes sign language', 'does not support sign language recognition', 'sign language recognition not supported', 'sign language recognition unsupported', 'no sign language recognition support', 'lacks sign language recognition', 'missing sign language recognition', 'sign language recognition disabled', 'no sign language recognition model', 'without sign language recognition support', 'does not provide sign language recognition', 'no automatic sign language recognition', 'sign language recognition not available', 'no sign language recognition capability', 'does not perform sign language recognition', 'never performs sign language recognition', 'does not translate sign language', 'without a sign language recognition model'])

    def test_generic_oracle(self):
        self.assertEqual(GENERIC_NAMES, ['recognize_sign_language', 'translate_sign_language', 'sign_language_recognize', 'sign_language_translate', 'predict_sign', 'sign_predict', 'classify_sign', 'sign_classify', 'recognize_sign', 'sign_recognize', 'recognize_fingerspelling', 'fingerspelling_recognize', 'sign_to_text', 'translate_sign', 'sign_translate', 'detect_sign_language', 'sign_language_detect', 'interpret_sign_language', 'sign_language_interpret', 'transcribe_sign_language', 'sign_language_transcribe', 'predict_sign_language', 'sign_language_predict', 'recognize_asl'])

    def test_class_oracle(self):
        self.assertEqual(DEDICATED_CLASSES, ['SignLanguageRecognizer', 'SignLanguageClassifier', 'SignLanguageTranslator', 'SignLanguageInterpreter', 'SignLanguageModel'])

    def cli(self, files, *args):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            return subprocess.run([sys.executable, '-m', 'sign_language_recognition_claim_audit', 'audit', directory, *args], capture_output=True, text=True)

    def test_cli_bad_json(self):
        result = self.cli({'README.md': 'sign language recognition'}, '--json')
        self.assertEqual(result.returncode, 2)
        finding = json.loads(result.stdout)[0]
        self.assertEqual(finding['id'], 'documented-sign-language-recognition-claim-false')
        self.assertEqual(finding['severity'], 'high')
        self.assertIn('verdict', finding)
        self.assertIn('message', finding)

    def test_cli_denial(self):
        result = self.cli({'README.md': 'does not recognize sign language', 'a.py': 'x.recognize_asl()'})
        self.assertEqual(result.returncode, 2)
        self.assertIn('documented-no-sign-language-recognition-claim-false', result.stdout)

    def test_cli_test_only(self):
        files = {'tests/fixture.md': 'sign language recognition'}
        self.assertEqual(self.cli(files).returncode, 0)
        result = self.cli(files, '--fail-on', 'medium')
        self.assertEqual(result.returncode, 2)
        self.assertIn('medium', result.stdout)

    def test_cli_pass(self):
        for files in ({}, {'README.md': 'neutral'}, {'README.md': 'does not recognize sign language'}, {'README.md': 'sign language recognition', 'a.py': 'x.recognize_asl()'}):
            self.assertEqual(self.cli(files).returncode, 0)

    def test_ignore(self):
        self.assertEqual(self.cli({'docs/bad.md': 'sign language recognition'}, '--ignore', 'docs', '--verbose').returncode, 0)

    def test_version(self):
        result = subprocess.run([sys.executable, '-m', 'sign_language_recognition_claim_audit', '--version'], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), '0.1.0')
        self.assertEqual(result.returncode, 0)

    def test_usage_io(self):
        for args in (['audit', '/does-not-exist'], ['invalid']):
            self.assertEqual(subprocess.run([sys.executable, '-m', 'sign_language_recognition_claim_audit', *args], capture_output=True).returncode, 1)

    def test_self_audit(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(claims((root / 'README.md').read_text()), ([], []))
        result = subprocess.run([sys.executable, '-m', 'sign_language_recognition_claim_audit', 'audit', str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_split_modules(self):
        self.assertEqual(self.cli({'README.md': 'sign language recognition', 'a.py': 'from x import SignLanguageModel\nm=SignLanguageModel()', 'b.py': 'm.run()'}).returncode, 2)

    def test_phrase_denial(self):
        self.assertEqual(claims('does not recognize sign language'), ([], ['does not recognize sign language']))

    def test_phrase_longest(self):
        self.assertEqual(claims('sign language recognition model'), (['sign language recognition'], []))

    def test_phrase_once(self):
        self.assertEqual(claims('recognize sign language'), (['recognize sign language'], []))

    def test_phrase_case(self):
        self.assertEqual(claims('SIGN LANGUAGE RECOGNITION'), (['sign language recognition'], []))

    def test_phrase_collision(self):
        self.assertEqual(claims('we provide a sign language interpreter for meetings'), (['sign language interpreter'], []))

    def test_phrase_fence(self):
        self.assertEqual(claims('```text\nsign language recognition\n```\n'), ([], []))

    def test_phrase_inline(self):
        self.assertEqual(claims('`sign language recognition`'), (['sign language recognition'], []))

    def test_phrase_hyphen(self):
        self.assertEqual(claims('recognize-sign-language'), ([], []))

    def test_evidence_true_0(self):
        self.assertEqual(has_evidence("import transformers as t\np=t.pipeline('video-classification', model='SIGN-model')\np('video')"), True)

    def test_evidence_true_1(self):
        self.assertEqual(has_evidence("from transformers import pipeline as p\np('video-classification', 'sign-model')('video')"), True)

    def test_evidence_true_2(self):
        self.assertEqual(has_evidence('from models import SignLanguageRecognizer as C\nm=C()\nm.run()'), True)

    def test_evidence_true_3(self):
        self.assertEqual(has_evidence('SignLanguageRecognizer().run()'), True)

    def test_evidence_true_4(self):
        self.assertEqual(has_evidence('from models import SignLanguageClassifier as C\nm=C()\nm.run()'), True)

    def test_evidence_true_5(self):
        self.assertEqual(has_evidence('SignLanguageClassifier().run()'), True)

    def test_evidence_true_6(self):
        self.assertEqual(has_evidence('from models import SignLanguageTranslator as C\nm=C()\nm.run()'), True)

    def test_evidence_true_7(self):
        self.assertEqual(has_evidence('SignLanguageTranslator().run()'), True)

    def test_evidence_true_8(self):
        self.assertEqual(has_evidence('from models import SignLanguageInterpreter as C\nm=C()\nm.run()'), True)

    def test_evidence_true_9(self):
        self.assertEqual(has_evidence('SignLanguageInterpreter().run()'), True)

    def test_evidence_true_10(self):
        self.assertEqual(has_evidence('from models import SignLanguageModel as C\nm=C()\nm.run()'), True)

    def test_evidence_true_11(self):
        self.assertEqual(has_evidence('SignLanguageModel().run()'), True)

    def test_evidence_true_12(self):
        self.assertEqual(has_evidence('import sign_language_translator as slt\nm=slt.models.Translator()\nm.translate()'), True)

    def test_evidence_true_13(self):
        self.assertEqual(has_evidence("from sign_language_translator import SLT as T\nT()('video')"), True)

    def test_evidence_true_14(self):
        self.assertEqual(has_evidence('import mediapipe as mp\nh=mp.solutions.hands.Hands()\nh.process(video)\nc.predict(x)'), True)

    def test_evidence_true_15(self):
        self.assertEqual(has_evidence('from mediapipe.solutions.hands import Hands as H\nH().process(video)\nc.predict(x)'), True)

    def test_evidence_true_16(self):
        self.assertEqual(has_evidence('import mediapipe as mp\nh=mp.solutions.holistic.Holistic()\nh.process(video)\nc.predict(x)'), True)

    def test_evidence_true_17(self):
        self.assertEqual(has_evidence('from mediapipe.solutions.holistic import Holistic as H\nH().process(video)\nc.predict(x)'), True)

    def test_evidence_true_18(self):
        self.assertEqual(has_evidence('x.recognize_sign_language()'), True)

    def test_evidence_true_19(self):
        self.assertEqual(has_evidence('from api import recognize_sign_language as f\nf()'), True)

    def test_evidence_true_20(self):
        self.assertEqual(has_evidence('x.translate_sign_language()'), True)

    def test_evidence_true_21(self):
        self.assertEqual(has_evidence('from api import translate_sign_language as f\nf()'), True)

    def test_evidence_true_22(self):
        self.assertEqual(has_evidence('x.sign_language_recognize()'), True)

    def test_evidence_true_23(self):
        self.assertEqual(has_evidence('from api import sign_language_recognize as f\nf()'), True)

    def test_evidence_true_24(self):
        self.assertEqual(has_evidence('x.sign_language_translate()'), True)

    def test_evidence_true_25(self):
        self.assertEqual(has_evidence('from api import sign_language_translate as f\nf()'), True)

    def test_evidence_true_26(self):
        self.assertEqual(has_evidence('x.predict_sign()'), True)

    def test_evidence_true_27(self):
        self.assertEqual(has_evidence('from api import predict_sign as f\nf()'), True)

    def test_evidence_true_28(self):
        self.assertEqual(has_evidence('x.sign_predict()'), True)

    def test_evidence_true_29(self):
        self.assertEqual(has_evidence('from api import sign_predict as f\nf()'), True)

    def test_evidence_true_30(self):
        self.assertEqual(has_evidence('x.classify_sign()'), True)

    def test_evidence_true_31(self):
        self.assertEqual(has_evidence('from api import classify_sign as f\nf()'), True)

    def test_evidence_true_32(self):
        self.assertEqual(has_evidence('x.sign_classify()'), True)

    def test_evidence_true_33(self):
        self.assertEqual(has_evidence('from api import sign_classify as f\nf()'), True)

    def test_evidence_true_34(self):
        self.assertEqual(has_evidence('x.recognize_sign()'), True)

    def test_evidence_true_35(self):
        self.assertEqual(has_evidence('from api import recognize_sign as f\nf()'), True)

    def test_evidence_true_36(self):
        self.assertEqual(has_evidence('x.sign_recognize()'), True)

    def test_evidence_true_37(self):
        self.assertEqual(has_evidence('from api import sign_recognize as f\nf()'), True)

    def test_evidence_true_38(self):
        self.assertEqual(has_evidence('x.recognize_fingerspelling()'), True)

    def test_evidence_true_39(self):
        self.assertEqual(has_evidence('from api import recognize_fingerspelling as f\nf()'), True)

    def test_evidence_true_40(self):
        self.assertEqual(has_evidence('x.fingerspelling_recognize()'), True)

    def test_evidence_true_41(self):
        self.assertEqual(has_evidence('from api import fingerspelling_recognize as f\nf()'), True)

    def test_evidence_true_42(self):
        self.assertEqual(has_evidence('x.sign_to_text()'), True)

    def test_evidence_true_43(self):
        self.assertEqual(has_evidence('from api import sign_to_text as f\nf()'), True)

    def test_evidence_true_44(self):
        self.assertEqual(has_evidence('x.translate_sign()'), True)

    def test_evidence_true_45(self):
        self.assertEqual(has_evidence('from api import translate_sign as f\nf()'), True)

    def test_evidence_true_46(self):
        self.assertEqual(has_evidence('x.sign_translate()'), True)

    def test_evidence_true_47(self):
        self.assertEqual(has_evidence('from api import sign_translate as f\nf()'), True)

    def test_evidence_true_48(self):
        self.assertEqual(has_evidence('x.detect_sign_language()'), True)

    def test_evidence_true_49(self):
        self.assertEqual(has_evidence('from api import detect_sign_language as f\nf()'), True)

    def test_evidence_true_50(self):
        self.assertEqual(has_evidence('x.sign_language_detect()'), True)

    def test_evidence_true_51(self):
        self.assertEqual(has_evidence('from api import sign_language_detect as f\nf()'), True)

    def test_evidence_true_52(self):
        self.assertEqual(has_evidence('x.interpret_sign_language()'), True)

    def test_evidence_true_53(self):
        self.assertEqual(has_evidence('from api import interpret_sign_language as f\nf()'), True)

    def test_evidence_true_54(self):
        self.assertEqual(has_evidence('x.sign_language_interpret()'), True)

    def test_evidence_true_55(self):
        self.assertEqual(has_evidence('from api import sign_language_interpret as f\nf()'), True)

    def test_evidence_true_56(self):
        self.assertEqual(has_evidence('x.transcribe_sign_language()'), True)

    def test_evidence_true_57(self):
        self.assertEqual(has_evidence('from api import transcribe_sign_language as f\nf()'), True)

    def test_evidence_true_58(self):
        self.assertEqual(has_evidence('x.sign_language_transcribe()'), True)

    def test_evidence_true_59(self):
        self.assertEqual(has_evidence('from api import sign_language_transcribe as f\nf()'), True)

    def test_evidence_true_60(self):
        self.assertEqual(has_evidence('x.predict_sign_language()'), True)

    def test_evidence_true_61(self):
        self.assertEqual(has_evidence('from api import predict_sign_language as f\nf()'), True)

    def test_evidence_true_62(self):
        self.assertEqual(has_evidence('x.sign_language_predict()'), True)

    def test_evidence_true_63(self):
        self.assertEqual(has_evidence('from api import sign_language_predict as f\nf()'), True)

    def test_evidence_true_64(self):
        self.assertEqual(has_evidence('x.recognize_asl()'), True)

    def test_evidence_true_65(self):
        self.assertEqual(has_evidence('from api import recognize_asl as f\nf()'), True)

    def test_evidence_false_0(self):
        self.assertEqual(has_evidence('import transformers'), False)

    def test_evidence_false_1(self):
        self.assertEqual(has_evidence('import mediapipe'), False)

    def test_evidence_false_2(self):
        self.assertEqual(has_evidence('import sign_language_translator'), False)

    def test_evidence_false_3(self):
        self.assertEqual(has_evidence('import cv2'), False)

    def test_evidence_false_4(self):
        self.assertEqual(has_evidence('import tensorflow'), False)

    def test_evidence_false_5(self):
        self.assertEqual(has_evidence('import torch'), False)

    def test_evidence_false_6(self):
        self.assertEqual(has_evidence('import mediapipe as mp\ng=mp.tasks.vision.GestureRecognizer()\ng.recognize()'), False)

    def test_evidence_false_7(self):
        self.assertEqual(has_evidence('import mediapipe as mp\ng=mp.tasks.vision.GestureRecognizer()\ng.recognize_for_video()'), False)

    def test_evidence_false_8(self):
        self.assertEqual(has_evidence('import mediapipe as mp\ng=mp.tasks.vision.GestureRecognizer()\ng.recognize_async()'), False)

    def test_evidence_false_9(self):
        self.assertEqual(has_evidence('cv2.findContours(x)\ncv2.convexityDefects(x)'), False)

    def test_evidence_false_10(self):
        self.assertEqual(has_evidence('import mediapipe as mp\nh=mp.solutions.hands.Hands()\nh.process(x)'), False)

    def test_evidence_false_11(self):
        self.assertEqual(has_evidence('pose.estimate(x)'), False)

    def test_evidence_false_12(self):
        self.assertEqual(has_evidence('face.detect(x)'), False)

    def test_evidence_false_13(self):
        self.assertEqual(has_evidence('hand.detect(x)'), False)

    def test_evidence_false_14(self):
        self.assertEqual(has_evidence("from transformers import pipeline\np=pipeline('translation',model='sign')\np(x)"), False)

    def test_evidence_false_15(self):
        self.assertEqual(has_evidence('translator.translate(x)'), False)

    def test_evidence_false_16(self):
        self.assertEqual(has_evidence('speech.recognize(x)'), False)

    def test_evidence_false_17(self):
        self.assertEqual(has_evidence('tts.speak(x)'), False)

    def test_evidence_false_18(self):
        self.assertEqual(has_evidence('keyword.spot(x)'), False)

    def test_evidence_false_19(self):
        self.assertEqual(has_evidence('speaker.verify(x)'), False)

    def test_evidence_false_20(self):
        self.assertEqual(has_evidence('audio.diarize(x)'), False)

    def test_evidence_false_21(self):
        self.assertEqual(has_evidence('c.predict(x)'), False)

    def test_evidence_false_22(self):
        self.assertEqual(has_evidence("from transformers import pipeline\np=pipeline('video-classification', model='actions')\np(x)"), False)

    def test_evidence_false_23(self):
        self.assertEqual(has_evidence('SignLanguageModel()'), False)

    def test_evidence_false_24(self):
        self.assertEqual(has_evidence('from sign_language_translator import SLT\nSLT()'), False)

    def test_evidence_false_25(self):
        self.assertEqual(has_evidence('"sign language recognition"\n# recognize sign language'), False)

    def test_evidence_false_26(self):
        self.assertEqual(has_evidence('recognize_sign_language'), False)

    def test_evidence_false_27(self):
        self.assertEqual(has_evidence('import subprocess\nsubprocess.run(["sign-cli"])'), False)

    def test_evidence_false_28(self):
        self.assertEqual(has_evidence('def recognize_sign_language(): pass\nrecognize_sign_language()'), False)

    def test_evidence_false_29(self):
        self.assertEqual(has_evidence('from x import recognize_sign_language\ndef recognize_sign_language(): pass\nrecognize_sign_language()'), False)

    def test_evidence_false_30(self):
        self.assertEqual(has_evidence('from mediapipe.solutions.hands import Hands\nclass Hands: pass\nh=Hands()\nh.process(x)\nc.predict(x)'), False)

    def test_evidence_false_31(self):
        self.assertEqual(has_evidence('from x import SignLanguageModel\nclass SignLanguageModel: pass\nSignLanguageModel().run()'), False)

    def test_evidence_false_32(self):
        self.assertEqual(has_evidence('from transformers import pipeline\ndef pipeline(): pass\npipeline("video-classification",model="sign")()'), False)

    def test_evidence_false_33(self):
        self.assertEqual(has_evidence('from sign_language_translator import SLT\nclass SLT: pass\nSLT()()'), False)

    def test_evidence_false_34(self):
        self.assertEqual(has_evidence('recognize_asl()'), False)

    def test_evidence_false_35(self):
        self.assertEqual(has_evidence('this is invalid python !'), False)

    def test_lowercase_imported_class(self):
        self.assertTrue(has_evidence('from sign_language_translator import translator\nm=translator()\nm.run()'))

    def test_landmark_with_context(self):
        self.assertTrue(has_evidence('from mediapipe.solutions.hands import Hands\nwith Hands() as h:\n    h.process(x)\nc.predict(x)'))

    def test_alias_shadow_pipeline(self):
        self.assertFalse(has_evidence('from transformers import pipeline as p\ndef p(): pass\np("video-classification", model="sign")()'))

    def test_alias_shadow_package_pair(self):
        self.assertFalse(has_evidence('from sign_language_translator import SLT as T\nclass T: pass\nT()()'))

    def test_docs_nested_and_ignore_source(self):
        files = {'docs/nested/claims.md': 'sign language recognition', 'src/model.py': 'x.recognize_asl()'}
        self.assertEqual(self.cli(files).returncode, 0)
        self.assertEqual(self.cli(files, '--ignore', 'src/').returncode, 2)

    def test_virtualenv_excluded(self):
        files = {'README.md': 'sign language recognition', 'custom-env/pyvenv.cfg': '', 'custom-env/model.py': 'x.recognize_asl()'}
        self.assertEqual(self.cli(files).returncode, 2)

    def test_scoped_docs(self):
        self.assertEqual(self.cli({'notes.md': 'sign language recognition'}).returncode, 0)

    def test_denials_removed_before_positive_matching(self):
        for phrase in NOSIGNLANGUAGE:
            self.assertEqual(claims(phrase), ([], [phrase]))

    def test_longest_plural(self):
        self.assertEqual(claims('sign language interpreters'), (['sign language interpreters'], []))
