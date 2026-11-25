#import <AppKit/AppKit.h>
#include <sys/resource.h>

static id editorField(id parent, NSString *value) {
    if ([parent respondsToSelector:@selector(accessibilityRole)] &&
        [[parent accessibilityRole] isEqual:NSAccessibilityTextAreaRole] &&
        (!value || [[parent accessibilityValue] isEqual:value]))
        return parent;
    if ([parent respondsToSelector:@selector(accessibilityChildren)]) {
        for (id child in [parent accessibilityChildren]) {
            id found = editorField(child, value);
            if (found) return found;
        }
    }
    return nil;
}

int scoop_editor_appkit_measure(void *rawView, int step) {
    if (step == 0) {
        struct rusage usage;
        return getrusage(RUSAGE_SELF, &usage) == 0 ? (int)(usage.ru_maxrss / 1024) : -1;
    }
    NSView<NSTextInputClient> *view = (__bridge NSView<NSTextInputClient> *)rawView;
    if (step == 1) {
        [view setMarkedText:@"zhong" selectedRange:NSMakeRange(5, 0) replacementRange:NSMakeRange(NSNotFound, 0)];
        return 0;
    }
    if (step == 2 || step == 4) {
        [view insertText:(step == 2 ? @"中" : @"q") replacementRange:NSMakeRange(NSNotFound, 0)];
        return 0;
    }
    if (step == 3) {
        id field = editorField(view, nil);
        NSString *value = [field accessibilityValue];
        return value ? (int)[value lengthOfBytesUsingEncoding:NSUTF8StringEncoding] : -1;
    }
    return -1;
}

// Run on the window owner thread using AppKit client methods.
int scoop_editor_appkit_probe(void *rawView, int step) {
    NSView<NSTextInputClient> *view = (__bridge NSView<NSTextInputClient> *)rawView;
    NSRange actual = NSMakeRange(NSNotFound, 0);
    if (step == 0) {
        NSAttributedString *line = [view attributedSubstringForProposedRange:NSMakeRange(0, 4) actualRange:&actual];
        if (![line.string isEqualToString:@"A🙂B"] || !NSEqualRanges(actual, NSMakeRange(0, 4))) return 1;
        if (!NSEqualRanges(view.selectedRange, NSMakeRange(3, 0))) return 2;
        if ([view attributedSubstringForProposedRange:NSMakeRange(5, 1) actualRange:&actual]) return 3;
        id field = editorField(view, @"一\r\nA🙂B\r\n末");
        if (!field || !NSEqualRanges([field accessibilitySelectedTextRange], NSMakeRange(6, 0))) return 4;
        if (![[field accessibilityRole] isEqualToString:NSAccessibilityTextAreaRole]) return 11;
        NSRect caret = [view firstRectForCharacterRange:view.selectedRange actualRange:&actual];
        if (NSIsEmptyRect(caret)) return 5;
        [view setMarkedText:@"候\n选" selectedRange:NSMakeRange(3, 0) replacementRange:NSMakeRange(1, 2)];
        return 0;
    }
    if (step == 1) {
        if (!view.hasMarkedText) return 6;
        [view insertText:@"字" replacementRange:NSMakeRange(NSNotFound, 0)];
        return 0;
    }
    if (step == 2) {
        NSAttributedString *line = [view attributedSubstringForProposedRange:NSMakeRange(0, 3) actualRange:&actual];
        if (![line.string isEqualToString:@"A字B"] || view.hasMarkedText) return 7;
        id field = editorField(view, @"一\r\nA字B\r\n末");
        if (!field) return 8;
        if (![field isAccessibilitySelectorAllowed:@selector(setAccessibilitySelectedTextRange:)]) return 10;
        // Accessibility enters from the AppKit run loop, outside the application's callback.
        dispatch_async(dispatch_get_main_queue(), ^{
            [field setAccessibilitySelectedTextRange:NSMakeRange(0, 3)];
        });
        return 0;
    }
    if (step == 3) {
        NSAttributedString *selected = [view attributedSubstringForProposedRange:NSMakeRange(0, 6) actualRange:&actual];
        return [selected.string isEqualToString:@"一\r\nA字B"] ? 0 : 9;
    }
    if (step == 4 || step == 5 || step == 7) {
        NSAttributedString *line = [view attributedSubstringForProposedRange:NSMakeRange(0, 2) actualRange:&actual];
        if (![line.string isEqualToString:@"aa"]) return 12;
        if (!NSEqualRanges(view.selectedRange, NSMakeRange(1, 0))) return 15;
        if (view.hasMarkedText) return 16;
        if (step == 5) [view setMarkedText:@"草" selectedRange:NSMakeRange(1, 0) replacementRange:NSMakeRange(NSNotFound, 0)];
        if (step == 7) [view insertText:@"X" replacementRange:NSMakeRange(NSNotFound, 0)];
        return 0;
    }
    NSAttributedString *line = [view attributedSubstringForProposedRange:NSMakeRange(0, 3) actualRange:&actual];
    if (step == 6) return view.hasMarkedText && [line.string isEqualToString:@"a草a"] ? 0 : 13;
    return step == 8 && !view.hasMarkedText && [line.string isEqualToString:@"aXa"] ? 0 : 14;
}
