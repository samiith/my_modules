#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__synopsis__    : ML related functions
__description__ :
__project__     : my_modules
__author__      : 'Samujjwal Ghosh'
__version__     :
__date__        : June 2018
__copyright__   : "Copyright (c) 2018"
__license__     : "Python"; (Licensed under the GNU LGPL v2.1 - http://www.gnu.org/licenses/lgpl.html)

__classes__     :

__variables__   :

__methods__     :

TODO            : 1.
"""

import re, math
from textblob import TextBlob as tb
from collections import OrderedDict, defaultdict
import numpy as np
import my_modules as mm


def select_tweets(test_unlabeled, unlabeled_pred, unlabeled_proba,
                  threshold=0.8):
    """Select new tweets with threshold to be added to train set"""
    print("Method: select_tweets(test_unlabeled,unlabeled_pred,"
          "unlabeled_proba,threshold=0.8)")

    if len(test_unlabeled) != len(unlabeled_pred) != len(unlabeled_proba):
        print("Lengths does not match: ", len(test_unlabeled),
              len(unlabeled_pred), len(unlabeled_proba))
        return False

    labelled_selected = OrderedDict()
    for i, (id, val) in enumerate(test_unlabeled.items()):
        if unlabeled_pred[i]:
            sel_cls = []
            for pos, prob in enumerate(unlabeled_proba[i]):
                if prob > threshold:
                    sel_cls.append(pos)

            if len(
                    sel_cls):  # adding only if at least one class has proba
                # > threshold
                val["classes"] = sel_cls
                val["probabilities"] = list(unlabeled_proba[i])
                labelled_selected[id] = val

    return labelled_selected


def max_add_unlabeled(train, test_unlabeled, unlabeled_pred, unlabeled_proba,
                      n_classes, max_add_portion=0.3, threshold=0.9):
    print("Method: max_add_unlabeled(train,test_unlabeled,unlabeled_pred,"
          "unlabeled_proba,max_add_portion=0.3,threshold=0.9,iter=0)")
    if threshold < 0.5:
        print("Threshold value very low: ", threshold)

    if len(test_unlabeled) != len(unlabeled_pred) != len(unlabeled_proba):
        print("Lengths does not match: ", len(test_unlabeled),
              len(unlabeled_pred), len(unlabeled_proba))
        return False

    print("Predicted class proportions:",
          mm.count_class(unlabeled_pred, n_classes))

    print("Selecting tweets with threshold = ", threshold,
          " to be added to train set")
    new_labeled_threshold = select_tweets(test_unlabeled, unlabeled_pred,
                                          unlabeled_proba, threshold=threshold)
    if len(new_labeled_threshold) < 1:
        print("No new tweet got selected, dict length: ",
              len(new_labeled_threshold))
        print("Returning original train set.")
        return train

    train_class_counts = mm.count_class(
        [val["classes"] for id, val in train.items()], n_classes)
    allowed_class_counts = [int(math.ceil(x * max_add_portion)) for x in
                            train_class_counts]
    new_labeled_threshold_class_counts = mm.count_class(
        [val["classes"] for id, val in new_labeled_threshold.items()],
        n_classes)
    print("Count class portions of selected tweets : ",
          new_labeled_threshold_class_counts)
    print("Allowed class portions : ", allowed_class_counts)
    sel_new = OrderedDict()
    for cls in range(
            n_classes):  # add maximum max_add_portion% of training data per
        # class
        # print(mm.count_class([val["classes"] for id,val in
        # new_labeled_threshold.items()],n_classes))
        if new_labeled_threshold_class_counts[cls] > allowed_class_counts[cls]:
            print("Current selected tweets count",
                  new_labeled_threshold_class_counts[cls],
                  "crosses maximum allowed",
                  int(train_class_counts[cls] * max_add_portion),
                  ", for class ", cls, ". Removing extra tweets.")
            i = 0
            for id, val in new_labeled_threshold.items():
                if i < allowed_class_counts[cls] and cls in val['classes']:
                    sel_new[id] = val
                    i = i + 1
        else:
            for id, val in new_labeled_threshold.items():
                sel_new[id] = val
    print(len(sel_new))
    new_labeled_threshold_class_counts = mm.count_class(
        [val["classes"] for id, val in sel_new.items()], n_classes)
    # save_json(sel_new,"sel_new_"+str(iter),tag=True)
    print("Count class portions of selected tweets: ",
          new_labeled_threshold_class_counts)
    print("Adding ", len(sel_new), " new selected tweets to train set")
    print(
        "Selected {:3.2f}% of new labeled tweets to be added to train "
        "set.".format(
            (len(sel_new) / len(test_unlabeled)) * 100))
    train = mm.merge_dicts(train, sel_new)
    return train


def supervised(train, test, train_tfidf_matrix, test_tfidf_matrix, n_classes,
               init_C=10, metric=False, grid=True):
    print("Method: supervised(train,test,train_tfidf_matrix,"
          "test_tfidf_matrix,init_C=10,probability=True,"
          "metric=False,grid=True)")
    from sklearn.preprocessing import MultiLabelBinarizer
    from sklearn.svm import SVC
    from sklearn.multiclass import OneVsRestClassifier
    # from scipy.stats import randint as sp_randint

    mlb = MultiLabelBinarizer()
    train_labels = [vals["classes"] for id, vals in train.items()]
    train_labels_bin = mlb.fit_transform(train_labels)

    print("\nAlgorithm: \t \t \t SVM")
    SVM = OneVsRestClassifier(SVC(kernel='linear', C=init_C, probability=True))
    if grid:
        print("Performing grid search...")
        SVM_params = [{'estimator__C':[10000, 1000, 100, 10, 1]}, ]
        # SVM_params = {'estimator__C': sp_randint(1, 10000)}
        SVM_grid = grid_search(SVM, SVM_params, train_tfidf_matrix,
                               train_labels_bin)
        SVM = OneVsRestClassifier(SVC(kernel='linear', C=SVM_grid['params'][
            'estimator__C'], probability=True))

    SVM_fit = SVM.fit(train_tfidf_matrix, train_labels_bin)
    SVM_pred = SVM_fit.predict(test_tfidf_matrix)
    SVM_proba = SVM_fit.predict_proba(test_tfidf_matrix)

    if metric:
        result = OrderedDict()
        test_labels = [vals["classes"] for id, vals in test.items()]
        mm.accuracy_multi(test_labels, mlb.inverse_transform(SVM_pred),
                          n_classes)
        result["SVM_metric"] = mm.sklearn_metrics(
            mlb.fit_transform(test_labels), SVM_pred)
        return result, mlb.inverse_transform(SVM_pred), SVM_proba
    return None, mlb.inverse_transform(SVM_pred), SVM_proba


def supervised_bin(train,test,train_tfidf_matrix,test_tfidf_matrix,n_classes,
                   class_id,init_C=10,metric=False,grid=True):
    print("Method: supervised_bin(train,test,train_tfidf_matrix,"
          "test_tfidf_matrix,init_C=10,probability=True,"
          "metric=False,grid=True)")
    from sklearn.svm import SVC
    from sklearn.multiclass import OneVsRestClassifier

    train_labels = []
    for i,val in train.items():
        if class_id in val["classes"]:
            train_labels.append(True)
        else:
            train_labels.append(False)

    print("\nAlgorithm: \t \t \t SVM")
    SVM = SVC(kernel='linear', C=init_C, probability=True)
    if grid:
        print("Performing grid search...")
        SVM_params = [{'C':[10000, 1000, 100, 10, 1]},]
        SVM_grid = grid_search(SVM,SVM_params,train_tfidf_matrix,train_labels)
        SVM = SVC(kernel='linear',C=SVM_grid['params']['C'],probability=True)
    SVM_fit = SVM.fit(train_tfidf_matrix, train_labels)
    SVM_pred = SVM_fit.predict(test_tfidf_matrix)
    SVM_proba = SVM_fit.predict_proba(test_tfidf_matrix)

    if metric:
        result = OrderedDict()
        # test_labels = [vals["classes"] for id, vals in test.items()]
        test_labels = []
        for i,val in test.items():
            if class_id in val["classes"]:
                test_labels.append(True)
            else:
                test_labels.append(False)

        mm.accuracy_multi(test_labels, SVM_pred,n_classes,multi=False)
        result["SVM_metric"] = mm.sklearn_metrics(test_labels, SVM_pred)
        return result, SVM_pred, SVM_proba
    return None, SVM_pred, SVM_proba


def supervised2(params,pkl_file=False):
    print("Method: supervised(train,test,train_tfidf_matrix,"
          "test_tfidf_matrix,init_C=10,probability=True,"
          "metric=False,grid=True)")
    from sklearn.preprocessing import MultiLabelBinarizer
    from sklearn.svm import SVC
    from sklearn.multiclass import OneVsRestClassifier
    # from scipy.stats import randint as sp_randint

    train = params["train"]
    test = params["test"]
    train_tfidf_matrix = params["train_tfidf_matrix"]
    test_tfidf_matrix = params["test_tfidf_matrix"]
    n_classes = params["n_classes"]
    init_C = params["init_C"]
    metric = params["metric"]

    mlb = MultiLabelBinarizer()
    train_labels = [vals["classes"] for id, vals in train.items()]
    train_labels_bin = mlb.fit_transform(train_labels)

    print("\nAlgorithm: \t \t \t SVM")
    SVM = None
    if pkl_file:
        if os.path.isfile(pkl_file):
            SVM = load_pickle(pkl_file)
    else:
        SVM = OneVsRestClassifier(SVC(kernel='linear', C=init_C, probability=True))
        pkl_file = "SVM"
        save_pickle(SVM, pkl_name, tag=False)

    SVM_fit = SVM.fit(train_tfidf_matrix, train_labels_bin)
    SVM_pred = SVM_fit.predict(test_tfidf_matrix)
    SVM_proba = SVM_fit.predict_proba(test_tfidf_matrix)

    if metric:
        result = OrderedDict()
        test_labels = [vals["classes"] for id, vals in test.items()]
        mm.accuracy_multi(test_labels, mlb.inverse_transform(SVM_pred),
                          n_classes)
        result["SVM_metric"] = mm.sklearn_metrics(
            mlb.fit_transform(test_labels), SVM_pred)
        return result, mlb.inverse_transform(SVM_pred), SVM_proba, SVM, pkl_file
    return None, mlb.inverse_transform(SVM_pred), SVM_proba, SVM, pkl_file


def supervised_parallel(train, test, train_tfidf_matrix, test_tfidf_matrix,
    n_classes,init_C=10, metric=False):
    from multiprocessing import Pool
    from itertools import product


    dataset = [10000, 1000, 100, 10, 1]
    agents = len(dataset)
    chunksize = 5

    all = defaultdict()

    all["train"] = train
    all["test"] = test
    all["train_tfidf_matrix"] = train_tfidf_matrix
    all["test_tfidf_matrix"] = test_tfidf_matrix
    all["n_classes"] = n_classes
    all["init_C"] = init_C
    all["metric"] = metric
    all["dataset"] = dataset

    result1 = pool.apply_async(solve1, [A])

    with Pool(processes=agents) as pool:
        result = pool.starmap(supervised2, all, chunksize)

    # Output the result
    print ('Result:  ' + str(result))


def grid_search(model, params, X_train, y_train, cv=5, score='f1'):
    print("Method: grid_search(model,params,X_train,y_train,cv=5,score='f1')")
    from sklearn.model_selection import GridSearchCV

    grid_results = OrderedDict()
    print("# Cross Validation set size: %s \n" % cv)
    print("Params: ", params)
    clf = GridSearchCV(model, params, cv=cv, scoring='%s_macro' % score)
    print("Grid search...")
    clf.fit(X_train, y_train)
    grid_results['params'] = clf.best_params_
    grid_results['score'] = clf.best_score_
    print("\nGrid scores on development set: ")
    means = clf.cv_results_['mean_test_score']
    stds = clf.cv_results_['std_test_score']
    for mean, std, params in zip(means, stds, clf.cv_results_['params']):
        print("%0.6f (+/-%0.06f) for %r"
              % (mean, std * 2, params))
    print()
    print("Best parameters set found on development set: ", clf.best_params_)

    return grid_results


def grid_search_rand(model, params, X_train, y_train, cv=5, score='f1',
                     n_iter_search=20):
    print(
        "Method: grid_search_rand(model,params,X_train,y_train,cv=5,"
        "score='f1',n_iter_search=20)")
    from sklearn.model_selection import RandomizedSearchCV

    grid_results = OrderedDict()
    print("Cross Validation set size: %s \n" % cv)
    print("Params: ", params)
    clf = RandomizedSearchCV(model, param_distributions=params, cv=cv,
                             n_iter=n_iter_search, scoring='%s_macro' % score)
    print("RandomizedSearchCV...")
    clf.fit(X_train, y_train)
    grid_results['params'] = clf.best_params_
    grid_results['score'] = clf.best_score_
    print("\nRandomizedSearchCV scores on development set: ")
    means = clf.cv_results_['mean_test_score']
    stds = clf.cv_results_['std_test_score']
    for mean, std, params in zip(means, stds, clf.cv_results_['params']):
        print("\t %0.9f (+/-%0.09f) for %r"
              % (mean, std * 2, params))
    print()
    print("Best parameters set found on development set: ", clf.best_params_)
    print()
    return grid_results


def add_features_matrix(train, train_matrix, n_classes, derived=True,
                        manual=True, length=True, k_unique_words=25):
    print("Method: add_features_matrix(train, train_matrix, n_classes, derived=True, manual=True, length=True, k_unique_words=25)")
    import json
    if manual:
        print("Adding Manual features...")
        loc = np.matrix(
            [[val["loc"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((train_matrix, loc), axis=1)

        medical = np.matrix(
            [[val["medical"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, medical), axis=1)

        number = np.matrix(
            [[val["number"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, number), axis=1)

        ra = np.matrix([[val["ra"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, ra), axis=1)

        rr = np.matrix([[val["rr"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, rr), axis=1)

        units = np.matrix(
            [[val["units"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, units), axis=1)

    if derived:
        print("Adding Derived features...")

        retweet_count_max = max(
            [val["retweet_count"] for id, val in train.items()])
        retweet_count = np.matrix(
            [[val["retweet_count"] / retweet_count_max] for id, val in
             train.items()])
        new = np.concatenate((train_matrix, retweet_count), axis=1)

        url = np.matrix(
            [[val["url"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, url), axis=1)

        phone = np.matrix(
            [[val["phone"] / val["word"]] for id, val in train.items()])
        new = np.concatenate((new, phone), axis=1)

        for i in range(n_classes):
            unique = np.matrix([val["unique"][i] / k_unique_words for id, val in
                                train.items()])
            new = np.concatenate((new, unique.T), axis=1)

        for i in range(n_classes):
            knn_votes = np.matrix(
                [val["knn_votes"][i] / k_unique_words for id, val in
                 train.items()])
            new = np.concatenate((new, knn_votes.T), axis=1)

    if length:
        print("Adding Length features...")

        char_max = max([val["char"] for id, val in train.items()])
        char = np.matrix(
            [[(val["char"] / char_max)] for id, val in train.items()])
        new = np.concatenate((train_matrix, char), axis=1)

        char_space_max = max([val["char_space"] for id, val in train.items()])
        char_space = np.matrix(
            [[(val["char_space"] / char_space_max)] for id, val in
             train.items()])
        new = np.concatenate((new, char_space), axis=1)

        word_max = max([val["word"] for id, val in train.items()])
        word = np.matrix(
            [[val["word"] / word_max] for id, val in train.items()])
        new = np.concatenate((new, word), axis=1)

    return new


def k_similar_tweets(train, test, k_similar=15):
    """Finds k_similar tweets in train for each test tweet using cosine
    similarity """
    print("Method: k_similar_tweets(train,test,k_similar=15)")
    k_sim_twts = OrderedDict()
    for t_twt_id, t_twt_val in test.items():
        i = 0
        sim_list = OrderedDict()
        for tr_twt_id, tr_twt_val in train.items():
            if t_twt_id == tr_twt_id:
                # print(t_twt_id,"Already exists in list,ignoring...")
                continue
            if i < k_similar:
                sim_list[tr_twt_id] = get_cosine(t_twt_val["parsed_tweet"],
                                                 tr_twt_val["parsed_tweet"])
                # sim_list[tr_twt_id]=get_jackard(t_twt_val["parsed_tweet"],
                # tr_twt_val["parsed_tweet"])
                i = i + 1
            else:
                new_sim_twt = get_cosine(t_twt_val["parsed_tweet"],
                                         tr_twt_val["parsed_tweet"])
                # new_sim_twt=get_jackard(t_twt_val["parsed_tweet"],
                # tr_twt_val["parsed_tweet"])
                for sim_id, sim_val in sim_list.items():
                    if new_sim_twt > sim_val:
                        del sim_list[sim_id]
                        sim_list[tr_twt_id] = new_sim_twt
                        break
        k_sim_twts[t_twt_id] = sim_list
    return k_sim_twts


def get_cosine(tweet1, tweet2):
    """calculates the cosine similarity between 2 tweets"""
    # print("Method: get_cosine(tweet1,tweet2)")
    from collections import Counter
    WORD = re.compile(r'\w+')
    vec1 = Counter(WORD.findall(tweet1))
    vec2 = Counter(WORD.findall(tweet2))

    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


def sim_tweet_class_vote(train, test, sim_vals, n_classes):
    """Returns the vote counts of train tweets of similar tweets for test
    tweets """
    print("Method: sim_tweet_class_vote(train,test,sim_vals)")
    class_votes = []
    for id, sim_dict in sim_vals.items():
        class_votes = [0] * n_classes
        for t_id in sim_dict.keys():
            for tr_cls in train[t_id]["classes"]:
                class_votes[tr_cls] = class_votes[tr_cls] + 1
        test[id]["knn_votes"] = class_votes
    return class_votes


def tf(word, blob):
    """computes "term frequency" which is the number of times a word appears
    in a document blob, normalized by dividing by the total number of
    words in blob."""
    return blob.words.count(word) / len(blob.words)


def n_containing(word, bloblist):
    """number of documents containing word"""
    return sum(1 for blob in bloblist if word in blob)


def idf(word, bloblist):
    """computes "inverse document frequency" which measures how common a word
    is among all documents in bloblist. The more common a word is, the lower
    its idf """
    return math.log(len(bloblist) / (1 + n_containing(word, bloblist)))


def tfidf(word, blob, bloblist):
    """computes the TF-IDF score. It is simply the product of tf and idf"""
    return tf(word, blob) * idf(word, bloblist)


def nltk_install(name):
    import nltk
    try:
        nltk.data.find('tokenizers/' + name)
    except LookupError:
        try:
            nltk.data.find('corpora/' + name)
        except LookupError:
            try:
                nltk.data.find('chunkers/' + name)
            except LookupError:
                try:
                    nltk.data.find('taggers/' + name)
                except LookupError:
                    print('Downloading NLTK data: ',name)
                    nltk.download(name)
    return True


def unique_words_class(class_corpuses, k_unique_words=25):
    """ Finds unique words for each class"""
    print("Method: unique_words_class(class_corpuses)")
    bloblist = []
    unique_words = defaultdict()

    import nltk
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        print('Downloading NLTK data...')
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')

    for cls_id, text in class_corpuses.items():
        bloblist.append(tb(" ".join(text)))
    for i, blob in enumerate(bloblist):
        unique_words[i] = []
        # print("\nTop words in class {}".format(i))
        scores = {word:tfidf(word, blob, bloblist) for word in blob.words}
        sorted_words = sorted(scores.items(), key=lambda x:x[1], reverse=True)
        for word, score in sorted_words[:k_unique_words]:
            # print("{},TF-IDF: {}".format(word,round(score,5)))
            unique_words[i].append(word)
    return unique_words


def vectorizer(list_items,n_grams=1,min_df=1,dense=True,sublinear_tf=False,smooth_idf=True):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from nltk.corpus import stopwords
    import string

    # stopword_list = stopwords.words('english') + list(string.punctuation) + [
        # 'rt', 'via', '& amp', '&amp', 'mr']

    tfidf_vectorizer = TfidfVectorizer(strip_accents= 'unicode',
                                       min_df       = min_df,
                                       # stop_words = stopword_list,
                                       decode_error = 'ignore',
                                       ngram_range  = (1, n_grams),
                                       sublinear_tf = sublinear_tf,
                                       smooth_idf   = smooth_idf)

    tfidf_matrix = tfidf_vectorizer.fit_transform(list_items)
    if dense:
        return tfidf_vectorizer, tfidf_matrix.todense()

    return tfidf_vectorizer, tfidf_matrix


def create_tf_idf(train, test, n_gram=1):
    '''Calculates tf-idf vectors for train'''
    print("Method: create_tf_idf(train,test)")
    from sklearn.feature_extraction.text import TfidfVectorizer
    tfidf_vectorizer = TfidfVectorizer(strip_accents='unicode',
                                       decode_error='ignore',
                                       ngram_range=(1, n_gram))
    train_tfidf_matrix = tfidf_vectorizer.fit_transform([vals["parsed_tweet"] for twt_id,vals in train.items()])
    # print(len(train),train_tfidf_matrix.shape)
    test_tfidf_matrix = tfidf_vectorizer.transform([vals["parsed_tweet"] for
                                                    twt_id, vals in
                                                    test.items()])
    return tfidf_vectorizer, train_tfidf_matrix.todense(),\
           test_tfidf_matrix.todense()


def find_word(tweet_text, word_list):
    tweet_text_blob = tb(tweet_text)
    word_count = 0
    for term in word_list:
        if term in tweet_text_blob.words.lower():
            word_count = word_count + 1
    return word_count


def unique_word_count_class(text, unique_words, n_classes):
    cls_counts = [0] * n_classes
    for word in text.split():
        for cls in range(len(unique_words)):
            if word in unique_words[cls]:
                cls_counts[cls] = cls_counts[cls] + 1
    return cls_counts


def derived_features(train,validation,test,n_classes,k_similar=15):
    sim_vals_train = k_similar_tweets(train, train, k_similar)
    sim_vals_validation = k_similar_tweets(train, validation, k_similar)
    sim_vals_test = k_similar_tweets(train, test, k_similar)

    sim_tweet_class_vote(train, train, sim_vals_train, n_classes)
    sim_tweet_class_vote(train, validation, sim_vals_validation, n_classes)
    sim_tweet_class_vote(train, test, sim_vals_test, n_classes)


def manual_features(train, unique_words, n_classes, feature_count=False):
    print("Method: manual_features(train,unique_words,feature_count=False)")

    units = tb('litre liter kg kilogram gram packet kilometer meter pack sets'
               ' ton meal equipment kit percentage')
    units = units.words + units.words.pluralize()
    units = find_synms_list(units)

    number = tb('lac lakh million thousand hundred')
    number = number.words + number.words.pluralize()
    number = find_synms_list(number)

    ra = tb('treat send sent sending supply offer distribute treat '
            'mobilize mobilized donate donated dispatch dispatched')
    ra = ra.words + ra.words.pluralize()
    ra = find_synms_list(ra)

    rr = tb('need requirement require ranout shortage scarcity')
    rr = rr.words + rr.words.pluralize()
    rr = find_synms_list(rr)

    medical = tb('medicine hospital medical doctor injection syringe ambulance'
                 ' antibiotic')
    medical = medical.words + medical.words.pluralize()
    medical = find_synms_list(medical)

    url = tb('urlurl')
    phone = tb('phonenumber')
    loc = tb('at')

    units_count = 0
    number_count = 0
    ra_count = 0
    rr_count = 0
    medical_count = 0
    loc_count = 0
    url_count = 0
    phone_count = 0
    feature_names = ['units', 'number', 'ra', 'rr', 'medical', 'loc', 'url',
                     'phone']
    feature_count_matrix = np.zeros((n_classes, (len(feature_names) + 1)))

    for i, vals in train.items():
        train[i]['units'] = find_word(vals['text'], units)
        train[i]['number'] = find_word(vals['text'], number)
        train[i]['ra'] = find_word(vals['text'], ra)
        train[i]['rr'] = find_word(vals['text'], rr)
        train[i]['medical'] = find_word(vals['text'], medical)
        train[i]['loc'] = find_word(vals['text'], loc)
        train[i]['url'] = find_word(vals['text'], url)
        train[i]['phone'] = find_word(vals['text'], phone)
        train[i]['word'] = len(vals["parsed_tweet"].split())
        train[i]['char'] = len(vals["parsed_tweet"]) - vals[
            "parsed_tweet"].count(' ')
        train[i]['unique'] = unique_word_count_class(vals["parsed_tweet"],
                                                      unique_words, n_classes)
        train[i]['char_space'] = len(vals["parsed_tweet"])
        if feature_count:
            for cls in train[i]['classes']:
                feature_count_matrix[cls][0] = feature_count_matrix[cls][0] +\
                                               train[i]['units']
                units_count = units_count + train[i]['units']
                feature_count_matrix[cls][1] = feature_count_matrix[cls][1] +\
                                               train[i]['number']
                number_count = number_count + train[i]['number']
                feature_count_matrix[cls][2] = feature_count_matrix[cls][2] +\
                                               train[i]['ra']
                ra_count = ra_count + train[i]['ra']
                feature_count_matrix[cls][3] = feature_count_matrix[cls][3] +\
                                               train[i]['rr']
                rr_count = rr_count + train[i]['rr']
                feature_count_matrix[cls][4] = feature_count_matrix[cls][4] +\
                                               train[i]['medical']
                medical_count = medical_count + train[i]['medical']
                feature_count_matrix[cls][5] = feature_count_matrix[cls][5] +\
                                               train[i]['loc']
                loc_count = loc_count + train[i]['loc']
                feature_count_matrix[cls][6] = feature_count_matrix[cls][6] +\
                                               train[i]['url']
                url_count = url_count + train[i]['url']
                feature_count_matrix[cls][7] = feature_count_matrix[cls][7] +\
                                               train[i]['phone']
                phone_count = phone_count + train[i]['phone']

    if feature_count:
        print(feature_names)
        print(feature_count_matrix)

        print(units_count)
        print(number_count)
        print(ra_count)
        print(rr_count)
        print(medical_count)
        print(loc_count)
        print(url_count)
        print(phone_count)
        for i in range(len(feature_count_matrix)):
            # for cls in train[id]['classes']:
            feature_count_matrix[i][0] = feature_count_matrix[i][0]/units_count
            feature_count_matrix[i][1] = feature_count_matrix[i][1]/number_count
            feature_count_matrix[i][2] = feature_count_matrix[i][2]/ra_count
            feature_count_matrix[i][3] = feature_count_matrix[i][3]/rr_count
            feature_count_matrix[i][4] = feature_count_matrix[i][4]/medical_count
            feature_count_matrix[i][5] = feature_count_matrix[i][5]/loc_count
            feature_count_matrix[i][6] = feature_count_matrix[i][6]/url_count
            feature_count_matrix[i][7] = feature_count_matrix[i][7]/phone_count
        print(feature_names)
        print(feature_count_matrix)


def classifier_agreement(c1_preds, c2_preds):
    assert (c1_preds.shape == c2_preds.shape)
    correct = 0
    # print(len(c1_preds))
    for i in range(c1_preds.shape[0]):
        for j in range(c1_preds.shape[1]):
            # print(c1_preds[i,j])
            # print(c1_preds[i])
            # print(c1_preds)
            if c1_preds[i, j] == c2_preds[i, j]:
                correct = correct + 1
    return correct


def find_synms_list(words,c=None):
    for word in words:
        words = words + mm.find_synms(word,c)

    words = mm.remove_dup_list(words, case=True)
    return words[0:c]


def find_synms(word,c=None,pos=None):
    from textblob import Word
    from itertools import chain

    synonyms = Word(word).get_synsets(pos)

    #for wl in synonyms:
     #   print(synonyms[0], wl.path_similarity(synonyms[0]), wl.lemma_names())

    lemmas = chain.from_iterable([word.lemma_names() for word in synonyms])
    lemmas = mm.remove_dup_list(lemmas, case=True)

    return lemmas[0:c]


def main():
    pass


if __name__ == "__main__": main()
